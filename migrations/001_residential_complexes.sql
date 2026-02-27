-- Residential Complexes table
CREATE TABLE IF NOT EXISTS residential_complexes (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    category TEXT NOT NULL,
    priority INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Junction table for PRO users (many-to-many)
CREATE TABLE IF NOT EXISTS user_residential_complexes (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    complex_id INTEGER NOT NULL REFERENCES residential_complexes(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, complex_id)
);

-- Add residential_complex column to users table for STANDARD users (single selection)
ALTER TABLE users ADD COLUMN IF NOT EXISTS residential_complex TEXT;

-- Indexes
CREATE INDEX IF NOT EXISTS idx_rc_category ON residential_complexes(category);
CREATE INDEX IF NOT EXISTS idx_rc_active ON residential_complexes(is_active);
CREATE INDEX IF NOT EXISTS idx_user_rc_user ON user_residential_complexes(user_id);

-- Insert residential complexes data
INSERT INTO residential_complexes (name, category, priority, is_active)
VALUES
    -- PREMIUM (priority 10)
    ('Esentai City', 'premium', 10, TRUE),
    ('Four Seasons', 'premium', 10, TRUE),
    ('Rams City', 'premium', 10, TRUE),
    ('Medeu Park', 'premium', 10, TRUE),
    ('Dostyk Residence', 'premium', 10, TRUE),
    ('Koktobe City', 'premium', 10, TRUE),
    ('Remizovka Hills', 'premium', 10, TRUE),
    ('Terracotta', 'premium', 10, TRUE),
    ('Orion', 'premium', 10, TRUE),
    ('Prime Park', 'premium', 10, TRUE),
    
    -- BUSINESS (priority 5)
    ('Комфорт Сити', 'business', 5, TRUE),
    ('Хан Тенгри', 'business', 5, TRUE),
    ('Асыл Тау', 'business', 5, TRUE),
    ('Нурлы Тау', 'business', 5, TRUE),
    ('Alma City', 'business', 5, TRUE),
    ('Шахристан', 'business', 5, TRUE),
    ('Аккент', 'business', 5, TRUE),
    ('Mega Towers', 'business', 5, TRUE),
    ('City Plus', 'business', 5, TRUE),
    ('Sensata City', 'business', 5, TRUE),
    
    -- COMFORT (priority 1)
    ('Алтын Булак', 'comfort', 1, TRUE),
    ('Орбита', 'comfort', 1, TRUE),
    ('Таугуль', 'comfort', 1, TRUE),
    ('Аксай', 'comfort', 1, TRUE),
    ('Жетысу', 'comfort', 1, TRUE),
    ('Алмагуль', 'comfort', 1, TRUE),
    ('Коктем', 'comfort', 1, TRUE),
    ('Айгерим', 'comfort', 1, TRUE),
    ('Сайран', 'comfort', 1, TRUE),
    ('Шугыла', 'comfort', 1, TRUE)
ON CONFLICT (name) DO NOTHING;
