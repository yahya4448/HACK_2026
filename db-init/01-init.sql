CREATE TABLE IF NOT EXISTS incidents (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255),
    status VARCHAR(50) DEFAULT 'open', -- open, acknowledged, resolved
    service VARCHAR(100),
    severity VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    acknowledged_at TIMESTAMP,
    resolved_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS alerts (
    id SERIAL PRIMARY KEY,
    incident_id INT REFERENCES incidents(id),
    raw_data JSONB,
    received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);