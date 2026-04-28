CREATE TABLE IF NOT EXISTS observations (
    station_id BIGINT NOT NULL REFERENCES stations(id) ON DELETE CASCADE,
    sensor_id BIGINT NULL REFERENCES station_sensors(id) ON DELETE SET NULL,
    dataset_id BIGINT NOT NULL REFERENCES datasets(id) ON DELETE RESTRICT,
    source_id BIGINT NOT NULL REFERENCES data_sources(id) ON DELETE RESTRICT,

    observed_at TIMESTAMPTZ NOT NULL,
    variable_code VARCHAR(50) NOT NULL,

    raw_value DOUBLE PRECISION NULL,
    cleaned_value DOUBLE PRECISION NULL,
    unit VARCHAR(50) NULL,

    qc_flag VARCHAR(20) NOT NULL DEFAULT 'unchecked',
    qc_notes TEXT NULL,

    ingest_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    payload_ref VARCHAR(255) NULL,

    PRIMARY KEY (station_id, variable_code, observed_at)
);

SELECT create_hypertable('observations', 'observed_at', if_not_exists => TRUE);

SELECT set_chunk_time_interval('observations', INTERVAL '7 days');

CREATE INDEX IF NOT EXISTS obs_station_time_idx
    ON observations (station_id, observed_at DESC);

CREATE INDEX IF NOT EXISTS obs_variable_time_idx
    ON observations (variable_code, observed_at DESC);

CREATE INDEX IF NOT EXISTS obs_dataset_time_idx
    ON observations (dataset_id, observed_at DESC);

CREATE INDEX IF NOT EXISTS obs_source_time_idx
    ON observations (source_id, observed_at DESC);

CREATE INDEX IF NOT EXISTS obs_qc_flag_idx
    ON observations (qc_flag);