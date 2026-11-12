# System Wspomagania Decyzji (SWD): Analiza Luki Kompetencyjnej i Priorytetyzacja Rozwoju w IT

Interaktywny system wspomagania decyzji zbudowany w środowisku **Microsoft Power BI**, wspierający kandydatów oraz specjalistów IT w wyborze technologii o najwyższym zwrocie z inwestycji w naukę (ROI).

---

## 1. Cel biznesowy i problem decyzyjny
Osoby wchodzące do branży IT lub planujące zmianę specjalizacji stają przed problemem nadmiaru technologii wymaganych w ogłoszeniach o pracę. System rozwiązuje problem **wielokryterialnego wyboru ścieżki rozwoju**, łącząc:
* indywidualny profil kompetencji użytkownika (samoocena w skali `0–5`),
* rzeczywiste wymagania rynkowe dla wybranej roli zawodowej,
* wybrany cel strategiczny użytkownika (**wejście do zawodu** vs **maksymalizacja wynagrodzenia**).

---

## 2. Architektura danych i model analityczny

### Źródło i struktura danych (`skill_benchmarks.csv`)
Model opiera się na zagregowanych danych rynkowych z ogłoszeń IT dla poszczególnych kategorii stanowisk (`role_category`) oraz poziomów doświadczenia (`experience_level`):
* `skill_name` – nazwa technologii lub kompetencji (np. SQL, Python, Power BI, Docker, English),
* `avg_required_level` – średni poziom biegłości wymagany przez pracodawców (skala `0–5`),
* `demand_pct` – odsetek ogłoszeń w danej kategorii wymagających danej umiejętności,
* `salary_lift_pct` – premia płacowa (względna różnica mediany wynagrodzeń w ofertach z daną umiejętnością względem mediany całego stanowiska).

### Parametry wejściowe użytkownika (14 suwaków + filtry)
System udostępnia interfejs pozwalający na wprowadzenie własnego profilu w skali **0–5** (od `0 – brak znajomości` do `5 – ekspert`) dla 14 grup technologicznych:
1. **Bazy danych i SQL** (SQL, PostgreSQL, MySQL, MSSQL, Oracle)
2. **Python i analiza danych** (Python, Pandas)
3. **Narzędzia BI i arkusze** (Power BI, Tableau, Excel)
4. **JavaScript / TypeScript**
5. **Frameworki Frontend** (React, Angular, Vue)
6. **HTML5 / CSS3**
7. **Technologie Mobile** (Kotlin, Swift, Flutter, React Native)
8. **Java i ekosystem JVM** (Java, Spring, Spring Boot)
9. **C# i .NET**
10. **Backend pozostałe** (Node.js, PHP, Go)
11. **Chmura obliczeniowa** (AWS, Azure, GCP)
12. **Kontenery i DevOps** (Docker, Kubernetes, Terraform)
13. **Linux i kontrola wersji** (Linux, Git)
14. **Język angielski** (English)

---

## 3. Logika decyzyjna i miary DAX

### Krok 1: Mapowanie poziomu użytkownika (`Poziom Użytkownika`)
Miara dynamicznie przypisuje wartość z odpowiedniego suwaka (`What-If Parameter`) do każdej technologii w modelu za pomocą funkcji `SWITCH(SELECTEDVALUE(...))`.

### Krok 2: Wyznaczenie luki kompetencyjnej
$$\text{Luka} = \max\left(0,\ \overline{\text{Wymagany Poziom}} - \text{Poziom Użytkownika}\right)$$
Jeśli użytkownik posiada już poziom równy lub wyższy od wymaganego na rynku, luka wynosi `0`, a technologia znika z rekomendacji do nauki.

### Krok 3: Indeks decyzyjny (`Priorytet Nauki`)
Bezwymiarowy wskaźnik punktowy porządkujący technologie od najbardziej opłacalnych do nauki w zależności od wybranej strategii (`TrybKariery`):

* **Tryb 1 – Pierwsza praca w zawodzie** *(maksymalizacja szansy na zatrudnienie)*:
  $$\text{Priorytet Nauki} = \text{Luka} \times \text{Popyt Rynkowy} \times 100$$

* **Tryb 2 – Maksymalizacja zarobków** *(balans popytu i premii płacowej)*:
  $$\text{Priorytet Nauki} = \text{Luka} \times \left(0{,}4 \times \text{Popyt Rynkowy} + 0{,}6 \times \max(0,\ \text{Premia Płacowa})\right) \times 100$$

---

## 4. Uruchomienie i podgląd systemu
* **Interaktywny dashboard (Power BI Service):** https://app.powerbi.com/groups/me/reports/5cd11685-01d8-4cf3-a64b-b82691f9c5cc/e96a7f699b3dc7d8e477?experience=power-bi *(wymaga zalogowania na konto Microsoft 365)*.
* **Podgląd interfejsu:**

![Podgląd dashboardu SWD](docs/dashboard_preview.png)

---

## 5. Autorzy
* Imię i Nazwisko – Projekt SWD
