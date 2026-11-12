CREATE TABLE IF NOT EXISTS dim_offers (
    offer_id INTEGER PRIMARY KEY,
    job_title TEXT NOT NULL,
    experience_level TEXT NOT NULL,
    salary_avg_pln REAL,
    work_mode TEXT
);

CREATE TABLE IF NOT EXISTS dim_skills (
    skill_id INTEGER PRIMARY KEY AUTOINCREMENT,
    skill_name TEXT UNIQUE NOT NULL,
    category TEXT DEFAULT 'Other'
);

CREATE TABLE IF NOT EXISTS fact_offer_skills (
    offer_id INTEGER,
    skill_id INTEGER,
    PRIMARY KEY (offer_id, skill_id),
    FOREIGN KEY (offer_id) REFERENCES dim_offers(offer_id),
    FOREIGN KEY (skill_id) REFERENCES dim_skills(skill_id)
);
