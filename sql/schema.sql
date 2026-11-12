PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS skill_benchmarks;
DROP TABLE IF EXISTS offer_skills;
DROP TABLE IF EXISTS offers;

-- 1. Tabela główna unikalnych ofert pracy (po deduplikacji w czasie)
CREATE TABLE offers (
    offer_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    role_category TEXT NOT NULL,          -- Ujednolicona rola (np. Data Analyst, Backend)
    experience_level TEXT NOT NULL,       -- junior, mid, senior
    company_name TEXT,
    company_size_clean TEXT,              -- Ujednolicona wielkość firmy
    city TEXT,
    country_code TEXT,
    workplace_type TEXT,                  -- remote, hybrid, office
    marker_icon TEXT,                     -- Główna kategoria z portalu
    salary_pln_min REAL,                  -- Znormalizowane miesięczne min w PLN
    salary_pln_max REAL,                  -- Znormalizowane miesięczne max w PLN
    salary_pln_avg REAL,                  -- Średnia z widełek w PLN
    contract_type TEXT,                   -- Preferowane B2B lub UoP
    first_seen_date TEXT NOT NULL,        -- Data pierwszego pojawienia się w zrzutach
    last_seen_date TEXT NOT NULL,         -- Data ostatniego pojawienia się w zrzutach
    days_active INTEGER NOT NULL          -- Czas życia ogłoszenia w dniach
);

-- 2. Tabela pomostowa umiejętności (1 wiersz = 1 technologia w ofercie)
CREATE TABLE offer_skills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    offer_id TEXT NOT NULL,
    skill_name TEXT NOT NULL,             -- Znormalizowana nazwa technologii (np. PostgreSQL)
    skill_level INTEGER NOT NULL,         -- Wymagany poziom w skali 1-5
    FOREIGN KEY (offer_id) REFERENCES offers(offer_id)
);

-- 3. Gotowa tabela decyzyjna dla Power BI (agregaty pod suwaki What-If)
CREATE TABLE skill_benchmarks (
    role_category TEXT NOT NULL,
    experience_level TEXT NOT NULL,
    skill_name TEXT NOT NULL,
    offers_count INTEGER NOT NULL,        -- Liczba ofert wymagających tej technologii
    total_role_offers INTEGER NOT NULL,   -- Łączna liczba ofert dla tej roli i poziomu
    demand_pct REAL NOT NULL,             -- % ofert wymagających tej umiejętności (0.0 - 1.0)
    avg_required_level REAL NOT NULL,     -- Średni wymagany poziom (1.0 - 5.0)
    median_salary_with_skill REAL,        -- Mediana płac PLN z tą technologią
    role_baseline_salary REAL,            -- Mediana płac PLN dla całej roli
    salary_lift_pct REAL,                 -- Premia płacowa (%) względem mediany roli
    PRIMARY KEY (role_category, experience_level, skill_name)
);

CREATE INDEX idx_offers_role_exp ON offers(role_category, experience_level);
CREATE INDEX idx_skills_offer ON offer_skills(offer_id);
CREATE INDEX idx_skills_name ON offer_skills(skill_name);