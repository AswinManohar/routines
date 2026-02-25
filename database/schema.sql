-- Routine Tracker Database Schema

-- Habits/Routines table
CREATE TABLE IF NOT EXISTS habits (
    id SERIAL PRIMARY KEY,
    habit_id VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    icon VARCHAR(10) DEFAULT '✨',
    is_recurring BOOLEAN DEFAULT FALSE,
    duration VARCHAR(20),
    target_days INTEGER, -- calculated from duration
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    archived_at TIMESTAMP
);

-- Daily completions table
CREATE TABLE IF NOT EXISTS completions (
    id SERIAL PRIMARY KEY,
    habit_id INTEGER REFERENCES habits(id) ON DELETE CASCADE,
    completion_date DATE NOT NULL,
    completion_percent INTEGER DEFAULT 0 CHECK (completion_percent >= 0 AND completion_percent <= 100),
    status VARCHAR(20) DEFAULT 'missed', -- completed, partial, missed
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(habit_id, completion_date)
);

-- Streak tracking
CREATE TABLE IF NOT EXISTS streaks (
    id SERIAL PRIMARY KEY,
    habit_id INTEGER REFERENCES habits(id) ON DELETE CASCADE,
    current_streak INTEGER DEFAULT 0,
    longest_streak INTEGER DEFAULT 0,
    last_completed DATE,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_completions_habit_date ON completions(habit_id, completion_date);
CREATE INDEX IF NOT EXISTS idx_completions_date ON completions(completion_date);
CREATE INDEX IF NOT EXISTS idx_habits_active ON habits(archived_at) WHERE archived_at IS NULL;

-- Function to calculate status from percentage
CREATE OR REPLACE FUNCTION calculate_status(pct INTEGER)
RETURNS VARCHAR(20) AS $$
BEGIN
    IF pct >= 75 THEN RETURN 'completed';
    ELSIF pct >= 30 THEN RETURN 'partial';
    ELSE RETURN 'missed';
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-set status
CREATE OR REPLACE FUNCTION set_completion_status()
RETURNS TRIGGER AS $$
BEGIN
    NEW.status := calculate_status(NEW.completion_percent);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_set_status ON completions;
CREATE TRIGGER trigger_set_status
    BEFORE INSERT OR UPDATE ON completions
    FOR EACH ROW
    EXECUTE FUNCTION set_completion_status();

-- Insert sample data
INSERT INTO habits (habit_id, name, icon, is_recurring, duration, target_days) VALUES
('morning-workout', 'Morning Workout', '🏃', true, '30 days', 30),
('deep-work', 'Deep Work Block', '🎯', true, '90 days', 90),
('learning', 'Learning / Reading', '📚', false, NULL, NULL),
('wind-down', 'Evening Wind-down', '🌙', true, '60 days', 60)
ON CONFLICT (habit_id) DO NOTHING;

-- Insert sample completions for this week
DO $$
DECLARE
    h_record RECORD;
    current_date_val DATE;
    day_offset INTEGER;
    random_pct INTEGER;
BEGIN
    FOR h_record IN SELECT id FROM habits LOOP
        FOR day_offset IN 0..6 LOOP
            current_date_val := CURRENT_DATE - day_offset;
            
            -- Skip future dates (only add data for today and past)
            IF day_offset = 0 OR (day_offset > 0 AND EXTRACT(DOW FROM current_date_val) != 0) THEN
                random_pct := floor(random() * 100)::INTEGER;
                
                INSERT INTO completions (habit_id, completion_date, completion_percent)
                VALUES (h_record.id, current_date_val, random_pct)
                ON CONFLICT (habit_id, completion_date) DO NOTHING;
            END IF;
        END LOOP;
    END LOOP;
END $$;

-- Initialize streaks
INSERT INTO streaks (habit_id, current_streak, longest_streak)
SELECT id, 
    floor(random() * 15)::INTEGER,
    floor(random() * 30 + 10)::INTEGER
FROM habits
ON CONFLICT DO NOTHING;
