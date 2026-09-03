CREATE TABLE IF NOT EXISTS recovery_daily (
    recovery_date TEXT PRIMARY KEY,
    sleep_start_at TEXT,
    sleep_end_at TEXT,
    sleep_duration_min INTEGER CHECK (sleep_duration_min IS NULL OR sleep_duration_min >= 0),
    sleep_score INTEGER CHECK (sleep_score IS NULL OR sleep_score BETWEEN 0 AND 100),
    resting_hr_bpm INTEGER CHECK (resting_hr_bpm IS NULL OR resting_hr_bpm > 0),
    hrv_overnight_ms REAL CHECK (hrv_overnight_ms IS NULL OR hrv_overnight_ms >= 0),
    hrv_status TEXT,
    training_readiness INTEGER CHECK (training_readiness IS NULL OR training_readiness BETWEEN 0 AND 100),
    body_battery_am INTEGER CHECK (body_battery_am IS NULL OR body_battery_am BETWEEN 0 AND 100),
    stress_avg INTEGER CHECK (stress_avg IS NULL OR stress_avg BETWEEN 0 AND 100),
    source_type TEXT NOT NULL,
    source_ref TEXT,
    notes TEXT,
    details_json TEXT NOT NULL DEFAULT '{}'
        CHECK (json_valid(details_json)),
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS recovery_observations (
    observation_id INTEGER PRIMARY KEY,
    recovery_date TEXT NOT NULL REFERENCES recovery_daily(recovery_date) ON DELETE CASCADE,
    observed_at TEXT NOT NULL,
    kind TEXT NOT NULL,
    body_area TEXT,
    severity INTEGER CHECK (severity IS NULL OR severity BETWEEN 0 AND 10),
    note TEXT NOT NULL,
    resolved_at TEXT
);

CREATE TABLE IF NOT EXISTS profile_entries (
    profile_entry_id INTEGER PRIMARY KEY,
    category TEXT NOT NULL,
    entry_key TEXT NOT NULL,
    value_text TEXT NOT NULL,
    valid_from TEXT NOT NULL,
    valid_to TEXT,
    source_type TEXT NOT NULL,
    source_ref TEXT,
    recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (entry_key, valid_from)
);

CREATE TABLE IF NOT EXISTS profile_measurements (
    measurement_id INTEGER PRIMARY KEY,
    measured_on TEXT NOT NULL,
    metric_key TEXT NOT NULL,
    value_num REAL NOT NULL,
    source_type TEXT NOT NULL,
    source_ref TEXT,
    recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (measured_on, metric_key, source_type)
);

CREATE TABLE IF NOT EXISTS events (
    event_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    event_date TEXT NOT NULL,
    event_type TEXT NOT NULL,
    distance_m INTEGER CHECK (distance_m IS NULL OR distance_m >= 0),
    priority TEXT,
    status TEXT NOT NULL,
    notes TEXT,
    UNIQUE (name, event_date)
);

CREATE TABLE IF NOT EXISTS training_summaries (
    summary_id INTEGER PRIMARY KEY,
    period_type TEXT NOT NULL,
    starts_on TEXT NOT NULL,
    ends_on TEXT NOT NULL,
    run_count INTEGER CHECK (run_count IS NULL OR run_count >= 0),
    distance_m REAL CHECK (distance_m IS NULL OR distance_m >= 0),
    duration_s INTEGER CHECK (duration_s IS NULL OR duration_s >= 0),
    load_value REAL,
    key_takeaway TEXT,
    details_json TEXT NOT NULL DEFAULT '{}'
        CHECK (json_valid(details_json)),
    UNIQUE (period_type, starts_on, ends_on)
);

CREATE TABLE IF NOT EXISTS training_blocks (
    block_id INTEGER PRIMARY KEY,
    event_id INTEGER REFERENCES events(event_id) ON DELETE SET NULL,
    name TEXT NOT NULL,
    objective TEXT NOT NULL,
    starts_on TEXT NOT NULL,
    ends_on TEXT NOT NULL,
    status TEXT NOT NULL,
    reassess_on TEXT,
    notes TEXT,
    UNIQUE (name, starts_on)
);

CREATE TABLE IF NOT EXISTS plan_weeks (
    week_id INTEGER PRIMARY KEY,
    block_id INTEGER NOT NULL REFERENCES training_blocks(block_id) ON DELETE CASCADE,
    starts_on TEXT NOT NULL,
    ends_on TEXT NOT NULL,
    objective TEXT,
    target_distance_m REAL CHECK (target_distance_m IS NULL OR target_distance_m >= 0),
    status TEXT NOT NULL,
    UNIQUE (block_id, starts_on)
);

CREATE TABLE IF NOT EXISTS plan_sessions (
    session_id INTEGER PRIMARY KEY,
    week_id INTEGER NOT NULL REFERENCES plan_weeks(week_id) ON DELETE CASCADE,
    planned_date TEXT NOT NULL,
    session_type TEXT NOT NULL,
    title TEXT NOT NULL,
    status TEXT NOT NULL,
    target_distance_m REAL CHECK (target_distance_m IS NULL OR target_distance_m >= 0),
    target_duration_s INTEGER CHECK (target_duration_s IS NULL OR target_duration_s >= 0),
    intensity TEXT,
    notes TEXT,
    UNIQUE (week_id, planned_date, title)
);

CREATE TABLE IF NOT EXISTS plan_items (
    item_id INTEGER PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES plan_sessions(session_id) ON DELETE CASCADE,
    sequence_no INTEGER NOT NULL CHECK (sequence_no > 0),
    item_type TEXT NOT NULL,
    target_distance_m REAL CHECK (target_distance_m IS NULL OR target_distance_m >= 0),
    target_duration_s INTEGER CHECK (target_duration_s IS NULL OR target_duration_s >= 0),
    intensity TEXT,
    instructions TEXT NOT NULL,
    UNIQUE (session_id, sequence_no)
);

CREATE TABLE IF NOT EXISTS activity_reviews (
    activity_review_id INTEGER PRIMARY KEY,
    plan_session_id INTEGER UNIQUE REFERENCES plan_sessions(session_id) ON DELETE SET NULL,
    source_activity_id TEXT NOT NULL UNIQUE,
    started_at TEXT NOT NULL,
    distance_m REAL CHECK (distance_m IS NULL OR distance_m >= 0),
    duration_s INTEGER CHECK (duration_s IS NULL OR duration_s >= 0),
    avg_hr_bpm INTEGER CHECK (avg_hr_bpm IS NULL OR avg_hr_bpm > 0),
    avg_pace_sec_per_km REAL CHECK (avg_pace_sec_per_km IS NULL OR avg_pace_sec_per_km > 0),
    rpe INTEGER CHECK (rpe IS NULL OR rpe BETWEEN 1 AND 10),
    outcome TEXT,
    details_json TEXT NOT NULL DEFAULT '{}'
        CHECK (json_valid(details_json)),
    reviewed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS plan_adjustments (
    adjustment_id INTEGER PRIMARY KEY,
    block_id INTEGER REFERENCES training_blocks(block_id) ON DELETE CASCADE,
    week_id INTEGER REFERENCES plan_weeks(week_id) ON DELETE CASCADE,
    session_id INTEGER REFERENCES plan_sessions(session_id) ON DELETE CASCADE,
    item_id INTEGER REFERENCES plan_items(item_id) ON DELETE CASCADE,
    adjusted_at TEXT NOT NULL,
    reason TEXT NOT NULL,
    decision TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_ref TEXT,
    CHECK (
        (block_id IS NOT NULL) +
        (week_id IS NOT NULL) +
        (session_id IS NOT NULL) +
        (item_id IS NOT NULL) = 1
    )
);

CREATE INDEX IF NOT EXISTS idx_recovery_daily_updated
    ON recovery_daily(updated_at);
CREATE INDEX IF NOT EXISTS idx_recovery_observations_date_kind
    ON recovery_observations(recovery_date, kind);
CREATE UNIQUE INDEX IF NOT EXISTS uq_recovery_observation_identity
    ON recovery_observations(
        recovery_date,
        observed_at,
        kind,
        ifnull(body_area, ''),
        note
    );
CREATE INDEX IF NOT EXISTS idx_profile_entries_current
    ON profile_entries(category, entry_key, valid_to);
CREATE INDEX IF NOT EXISTS idx_profile_measurements_metric_date
    ON profile_measurements(metric_key, measured_on DESC);
CREATE INDEX IF NOT EXISTS idx_events_date_status
    ON events(event_date, status);
CREATE INDEX IF NOT EXISTS idx_training_summaries_period
    ON training_summaries(period_type, starts_on DESC);
CREATE INDEX IF NOT EXISTS idx_training_blocks_status_dates
    ON training_blocks(status, starts_on, ends_on);
CREATE INDEX IF NOT EXISTS idx_plan_weeks_block_dates
    ON plan_weeks(block_id, starts_on);
CREATE INDEX IF NOT EXISTS idx_plan_sessions_date_status
    ON plan_sessions(planned_date, status);
CREATE INDEX IF NOT EXISTS idx_plan_items_session_sequence
    ON plan_items(session_id, sequence_no);
CREATE INDEX IF NOT EXISTS idx_activity_reviews_started
    ON activity_reviews(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_adjustments_block
    ON plan_adjustments(block_id, adjusted_at DESC);
CREATE INDEX IF NOT EXISTS idx_adjustments_week
    ON plan_adjustments(week_id, adjusted_at DESC);
CREATE INDEX IF NOT EXISTS idx_adjustments_session
    ON plan_adjustments(session_id, adjusted_at DESC);
CREATE INDEX IF NOT EXISTS idx_adjustments_item
    ON plan_adjustments(item_id, adjusted_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS uq_adjustments_source_ref
    ON plan_adjustments(source_type, source_ref)
    WHERE source_ref IS NOT NULL;

CREATE VIEW IF NOT EXISTS v_recovery_recent AS
SELECT
    r.*,
    (
        SELECT group_concat(o.kind || ': ' || o.note, ' | ')
        FROM recovery_observations AS o
        WHERE o.recovery_date = r.recovery_date
    ) AS observations
FROM recovery_daily AS r;

CREATE VIEW IF NOT EXISTS v_current_profile AS
SELECT *
FROM profile_entries
WHERE valid_to IS NULL;

CREATE VIEW IF NOT EXISTS v_current_plan AS
SELECT
    b.block_id,
    b.name AS block_name,
    b.objective AS block_objective,
    b.reassess_on,
    w.week_id,
    w.starts_on AS week_starts_on,
    w.ends_on AS week_ends_on,
    w.objective AS week_objective,
    s.session_id,
    s.planned_date,
    s.session_type,
    s.title,
    s.status AS session_status,
    s.target_distance_m,
    s.target_duration_s,
    s.intensity,
    s.notes
FROM training_blocks AS b
JOIN plan_weeks AS w ON w.block_id = b.block_id
LEFT JOIN plan_sessions AS s ON s.week_id = w.week_id
WHERE b.status = 'active';

CREATE VIEW IF NOT EXISTS v_dashboard AS
SELECT
    (SELECT max(recovery_date) FROM recovery_daily) AS latest_recovery_date,
    (SELECT sleep_score FROM recovery_daily ORDER BY recovery_date DESC LIMIT 1) AS latest_sleep_score,
    (SELECT training_readiness FROM recovery_daily ORDER BY recovery_date DESC LIMIT 1) AS latest_training_readiness,
    (SELECT name FROM training_blocks WHERE status = 'active' ORDER BY starts_on DESC LIMIT 1) AS active_block,
    (SELECT planned_date FROM plan_sessions WHERE status = 'planned' ORDER BY planned_date LIMIT 1) AS next_session_date,
    (SELECT title FROM plan_sessions WHERE status = 'planned' ORDER BY planned_date LIMIT 1) AS next_session_title;
