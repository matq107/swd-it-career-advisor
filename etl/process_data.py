import json
import os
import re
import sqlite3
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterator, List, Tuple

import numpy as np
import pandas as pd
from tqdm import tqdm

# Ścieżki projektu
BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
SCHEMA_PATH = BASE_DIR / "sql" / "schema.sql"
DB_PATH = PROCESSED_DIR / "it_market.db"

# Przybliżone średnie kursy walut z lat 2021-2023 do normalizacji widełek na PLN
CURRENCY_RATES = {
    "pln": 1.0,
    "eur": 4.60,
    "usd": 4.25,
    "gbp": 5.35,
    "chf": 4.65,
}

# Słownik normalizacji najczęstszych literówek i wariantów nazw technologii
SKILL_ALIASES = {
    "js": "JavaScript",
    "javascript (es6+)": "JavaScript",
    "es6+": "JavaScript",
    "ts": "TypeScript",
    "pyhon": "Python",
    "python 3": "Python",
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "ms sql": "MSSQL",
    "ms sql server": "MSSQL",
    "sql server": "MSSQL",
    "powerbi": "Power BI",
    "power bi": "Power BI",
    "amazon web services": "AWS",
    "aws": "AWS",
    "google cloud": "GCP",
    "google cloud platform": "GCP",
    "gcp": "GCP",
    "microsoft azure": "Azure",
    "azure": "Azure",
    "k8s": "Kubernetes",
    "kubernetes": "Kubernetes",
    "gitflow": "Git",
    "git": "Git",
    "react.js": "React",
    "reactjs": "React",
    "vue.js": "Vue",
    "vuejs": "Vue",
    "node.js": "Node.js",
    "nodejs": "Node.js",
    "c#": "C#",
    ".net core": ".NET",
    ".net": ".NET",
}


def map_role_category(title: str, marker_icon: str) -> str:
    """Przypisuje chaotyczny tytuł ogłoszenia do jednej z głównych ścieżek kariery."""
    t = (title or "").lower()
    m = (marker_icon or "").lower()

    if any(k in t for k in ["data analyst", "analityk danych", "bi analyst", "business intelligence", "data analytics"]):
        return "Data Analyst / BI"
    if any(k in t for k in ["data scientist", "machine learning", "ml engineer", "ai engineer", "deep learning"]):
        return "Data Science / AI"
    if any(k in t for k in ["data engineer", "big data", "etl", "hurtowni danych"]):
        return "Data Engineer"
    if any(k in t for k in ["devops", "sre", "site reliability", "cloud engineer", "platform engineer"]):
        return "DevOps / Cloud"
    if any(k in t for k in ["qa", "tester", "test automation", "quality assurance"]):
        return "QA / Testing"
    if any(k in t for k in ["security", "cyber", "pentester", "soc analyst"]):
        return "Cybersecurity"
    if any(k in t for k in ["product manager", "product owner", "scrum master", "project manager"]):
        return "PM / Product"
    if any(k in t for k in ["ux", "ui", "product designer"]):
        return "UX / UI Design"
    if any(k in t for k in ["frontend", "front-end", "react", "angular", "vue"]):
        return "Frontend Developer"
    if any(k in t for k in ["fullstack", "full-stack", "full stack"]):
        return "Fullstack Developer"
    if any(k in t for k in ["backend", "back-end", "java", "python", ".net", "c#", "golang", "php", "node"]):
        return "Backend Developer"
    if any(k in t for k in ["android", "ios", "flutter", "react native", "mobile"]):
        return "Mobile Developer"

    # Fallback na kategorię główną z portalu
    if m == "data":
        return "Data Analyst / BI"
    if m == "devops":
        return "DevOps / Cloud"
    if m == "testing":
        return "QA / Testing"
    return "Other"


def normalize_skill(name: str) -> str:
    if not name:
        return ""
    cleaned = name.strip()
    key = cleaned.lower()
    return SKILL_ALIASES.get(key, cleaned)


def extract_salary_pln(employment_types: list) -> Tuple[float, float, float, str]:
    """Wyciąga widełki płacowe i przelicza je na miesięczne PLN (preferując B2B, potem UoP)."""
    if not employment_types or not isinstance(employment_types, list):
        return None, None, None, None

    # Sortujemy tak, aby preferować b2b, następnie permanent (UoP)
    priority = {"b2b": 1, "permanent": 2, "mandate_contract": 3}
    valid_contracts = []

    for emp in employment_types:
        sal = emp.get("salary")
        if sal and isinstance(sal, dict):
            s_from = sal.get("from")
            s_to = sal.get("to")
            curr = (sal.get("currency") or "pln").lower()
            c_type = emp.get("type") or "unknown"
            if s_from is not None and s_to is not None and curr in CURRENCY_RATES:
                rate = CURRENCY_RATES[curr]
                # Odsiewamy stawki godzinowe (< 500 PLN) oraz roczne (> 150 000 PLN/mies)
                min_pln = float(s_from) * rate
                max_pln = float(s_to) * rate
                if 1500 <= min_pln <= 120000 and 1500 <= max_pln <= 150000:
                    valid_contracts.append((priority.get(c_type, 9), min_pln, max_pln, c_type))

    if not valid_contracts:
        return None, None, None, None

    valid_contracts.sort(key=lambda x: x[0])
    _, min_pln, max_pln, c_type = valid_contracts[0]
    return round(min_pln, 2), round(max_pln, 2), round((min_pln + max_pln) / 2.0, 2), c_type


def iter_json_files(limit_files: int = None) -> Iterator[Tuple[str, list]]:
    """Iteruje po wszystkich plikach YYYY-MM-DD.json (zarówno w archiwach .zip, jak i rozpakowanych)."""
    tasks = []

    # 1. Szukamy archiwów .zip w data/raw
    zip_files = sorted(RAW_DIR.glob("*.zip"))
    for zpath in zip_files:
        with zipfile.ZipFile(zpath, "r") as zf:
            json_names = sorted(
                [n for n in zf.namelist() if n.endswith(".json") and not "__MACOSX" in n]
            )
            for name in json_names:
                tasks.append(("zip", zpath, name))

    # 2. Jeśli brak .zip, szukamy rozpakowanych plików .json w podfolderach
    if not tasks:
        json_paths = sorted(RAW_DIR.rglob("*.json"))
        for p in json_paths:
            tasks.append(("file", p, p.name))

    if limit_files:
        tasks = tasks[:limit_files]

    for source_type, container_path, inner_name in tqdm(tasks, desc="Przetwarzanie plików dziennych"):
        date_match = re.search(r"(\d{4}-\d{2}-\d{2})", inner_name)
        snapshot_date = date_match.group(1) if date_match else "1970-01-01"

        try:
            if source_type == "zip":
                with zipfile.ZipFile(container_path, "r") as zf:
                    raw_bytes = zf.read(inner_name)
                    records = json.loads(raw_bytes.decode("utf-8"))
            else:
                with open(container_path, "r", encoding="utf-8") as f:
                    records = json.load(f)

            if isinstance(records, list):
                yield snapshot_date, records
        except Exception as e:
            print(f"[OSTRZEŻENIE] Pominięto uszkodzony plik {inner_name}: {e}")


def run_etl(limit_files: int = None):
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    # Słownik unikalnych ofert w pamięci (klucz: offer_id lub firma+tytuł)
    unique_offers: Dict[str, dict] = {}
    seen_offer_ids: Dict[str, str] = {}
    offer_skills_map: Dict[str, List[Tuple[str, int]]] = {}

    for snapshot_date, records in iter_json_files(limit_files=limit_files):
        for rec in records:
            # Deduplikacja wielolokalizacyjna, czasowa oraz po ID (odświeżenia ofert)
            company = (rec.get("company_name") or "Unknown").strip()
            title = (rec.get("title") or "").strip()
            pub_date = (rec.get("published_at") or snapshot_date)[:10]
            dedup_key = f"{company.lower()}|{title.lower()}|{pub_date}"
            raw_id = str(rec.get("id") or abs(hash(dedup_key)))

            existing_key = dedup_key if dedup_key in unique_offers else seen_offer_ids.get(raw_id)
            if existing_key:
                # Aktualizujemy tylko datę pierwszego i ostatniego pojawienia się oferty
                if snapshot_date < unique_offers[existing_key]["first_seen_date"]:
                    unique_offers[existing_key]["first_seen_date"] = snapshot_date
                if snapshot_date > unique_offers[existing_key]["last_seen_date"]:
                    unique_offers[existing_key]["last_seen_date"] = snapshot_date
                continue

            seen_offer_ids[raw_id] = dedup_key
            offer_id = raw_id
            marker_icon = rec.get("marker_icon") or ""
            role_cat = map_role_category(title, marker_icon)
            exp_level = (rec.get("experience_level") or "mid").lower()
            if exp_level not in {"junior", "mid", "senior"}:
                exp_level = "mid"

            sal_min, sal_max, sal_avg, c_type = extract_salary_pln(rec.get("employment_types"))

            unique_offers[dedup_key] = {
                "offer_id": offer_id,
                "title": title,
                "role_category": role_cat,
                "experience_level": exp_level,
                "company_name": company,
                "company_size_clean": str(rec.get("company_size") or "Unknown").strip(),
                "city": (rec.get("city") or "Unknown").strip(),
                "country_code": (rec.get("country_code") or "PL").upper(),
                "workplace_type": (rec.get("workplace_type") or "unknown").lower(),
                "marker_icon": marker_icon,
                "salary_pln_min": sal_min,
                "salary_pln_max": sal_max,
                "salary_pln_avg": sal_avg,
                "contract_type": c_type,
                "first_seen_date": snapshot_date,
                "last_seen_date": snapshot_date,
            }

            # Zapisujemy umiejętności (skala 1-5)
            skills_raw = rec.get("skills") or []
            parsed_skills = []
            seen_skill_names = set()
            for sk in skills_raw:
                if isinstance(sk, dict):
                    s_name = normalize_skill(sk.get("name"))
                    s_lvl = sk.get("level")
                    if s_name and isinstance(s_lvl, (int, float)) and 1 <= int(s_lvl) <= 5:
                        if s_name not in seen_skill_names:
                            seen_skill_names.add(s_name)
                            parsed_skills.append((s_name, int(s_lvl)))
            offer_skills_map[offer_id] = parsed_skills

    print(f"\nZebrano {len(unique_offers)} unikalnych ofert. Budowanie tabel analitycznych...")

    # Konwersja do DataFrame
    offers_df = pd.DataFrame(list(unique_offers.values()))
    offers_df["days_active"] = (
        pd.to_datetime(offers_df["last_seen_date"]) - pd.to_datetime(offers_df["first_seen_date"])
    ).dt.days + 1

    skills_rows = []
    for oid, sk_list in offer_skills_map.items():
        for s_name, s_lvl in sk_list:
            skills_rows.append({"offer_id": oid, "skill_name": s_name, "skill_level": s_lvl})
    skills_df = pd.DataFrame(skills_rows)

    # Wyliczanie tabeli decyzyjnej skill_benchmarks dla Power BI
    merged = skills_df.merge(
        offers_df[["offer_id", "role_category", "experience_level", "salary_pln_avg"]],
        on="offer_id",
        how="inner",
    )

    role_totals = (
        offers_df.groupby(["role_category", "experience_level"])
        .agg(
            total_role_offers=("offer_id", "count"),
            role_baseline_salary=("salary_pln_avg", "median"),
        )
        .reset_index()
    )

    skill_stats = (
        merged.groupby(["role_category", "experience_level", "skill_name"])
        .agg(
            offers_count=("offer_id", "count"),
            avg_required_level=("skill_level", "mean"),
            median_salary_with_skill=("salary_pln_avg", "median"),
        )
        .reset_index()
    )

    benchmarks_df = skill_stats.merge(role_totals, on=["role_category", "experience_level"], how="inner")
    # Odsiewamy niszowe literówki występujące w mniej niż 5 ofertach danej roli
    benchmarks_df = benchmarks_df[benchmarks_df["offers_count"] >= 5].copy()
    benchmarks_df["demand_pct"] = (benchmarks_df["offers_count"] / benchmarks_df["total_role_offers"]).round(4)
    benchmarks_df["avg_required_level"] = benchmarks_df["avg_required_level"].round(2)
    benchmarks_df["salary_lift_pct"] = (
        (benchmarks_df["median_salary_with_skill"] - benchmarks_df["role_baseline_salary"])
        / benchmarks_df["role_baseline_salary"]
    ).round(4)

    # 1. Zapis do bazy SQLite
    if DB_PATH.exists():
        DB_PATH.unlink()
    conn = sqlite3.connect(DB_PATH)
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())

    offers_df.to_sql("offers", conn, if_exists="append", index=False)
    skills_df.to_sql("offer_skills", conn, if_exists="append", index=False)
    benchmarks_df.to_sql("skill_benchmarks", conn, if_exists="append", index=False)
    conn.close()

    # 2. Eksport czystych CSV do data/processed/ pod Power BI
    offers_df.to_csv(PROCESSED_DIR / "offers.csv", index=False)
    skills_df.to_csv(PROCESSED_DIR / "offer_skills.csv", index=False)
    benchmarks_df.to_csv(PROCESSED_DIR / "skill_benchmarks.csv", index=False)

    print("Gotowe! Wygenerowane pliki:")
    print(f" - Baza SQLite: {DB_PATH}")
    print(f" - CSV dla Power BI: {PROCESSED_DIR / 'skill_benchmarks.csv'} ({len(benchmarks_df)} wierszy)")


if __name__ == "__main__":
    # NA START: ustaw limit_files=10, żeby przetestować w 3 sekundy.
    # Gdy wszystko zadziała, zmień na limit_files=None, aby przetworzyć całe 2021-2023.
    run_etl(limit_files=None)