# System Wspomagania Decyzji – Doradca Ścieżki Kariery IT

Projekt realizowany w ramach przedmiotu **Systemy Wspomagania Decyzji (SWD)**. System analizuje oferty pracy dla programistów i rekomenduje kandydatowi kolejność nauki brakujących technologii na podstawie wielokryterialnej oceny (popyt rynkowy, wpływ na wynagrodzenie, próg wejścia).

## Struktura projektu
* `data/` – surowe i przetworzone zbiory danych (schemat gwiazdy dla Power BI)
* `etl/` – skrypty w Pythonie odpowiedzialne za czyszczenie danych i zasilenie bazy
* `sql/` – schemat relacyjnej bazy danych SQLite
* `web/` – prosty interfejs webowy osadzający dashboard Power BI
* `docs/` – dokumentacja projektowa oraz diagramy BPMN i UML
