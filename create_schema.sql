-- AVA OLO Agricultural Assistant Database Schema - Modular Architecture
-- Updated schema for new modular system

-- Farmers table - Croatian farmers using AVA OLO
CREATE TABLE ava_farmers (
    id SERIAL PRIMARY KEY,
    state_farm_number VARCHAR(50) UNIQUE,  -- Croatian state farm registration number
    farm_name VARCHAR(100),
    manager_name VARCHAR(50),
    manager_last_name VARCHAR(50),
    street_and_no VARCHAR(100),
    village VARCHAR(100),
    postal_code VARCHAR(20),
    city VARCHAR(100),
    country VARCHAR(50) DEFAULT 'Croatia',
    vat_no VARCHAR(50) UNIQUE,
    email VARCHAR(100),
    phone VARCHAR(20),
    wa_phone_number VARCHAR(20),  -- WhatsApp number for AVA integration
    notes TEXT,
    platform VARCHAR(10) DEFAULT 'AVA',
    farmer_type VARCHAR(50),  -- 'grain', 'vegetable', 'livestock', 'mixed'
    farmer_type_secondary VARCHAR(50),
    total_hectares DECIMAL(10, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Fields table - farmer's agricultural fields
CREATE TABLE ava_fields (
    field_id SERIAL PRIMARY KEY,
    farmer_id INTEGER REFERENCES ava_farmers(id) ON DELETE CASCADE,
    field_name VARCHAR(100) NOT NULL,
    field_size DECIMAL(10, 2),  -- Size in hectares
    field_location VARCHAR(200),
    soil_type VARCHAR(50),  -- 'clay', 'sand', 'loam', etc.
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Crop catalog - types of crops that can be grown
CREATE TABLE ava_crops (
    id SERIAL PRIMARY KEY,
    crop_name VARCHAR(100) NOT NULL UNIQUE,
    crop_type VARCHAR(50),  -- 'grain', 'vegetable', 'fruit', 'forage'
    typical_cycle_days INTEGER,  -- 120 for corn, 200 for wheat
    croatian_name VARCHAR(100),  -- Local Croatian name
    description TEXT
);

-- Field crops - what's currently planted in each field
CREATE TABLE ava_field_crops (
    id SERIAL PRIMARY KEY,
    field_id INTEGER REFERENCES ava_fields(field_id) ON DELETE CASCADE,
    crop_name VARCHAR(100) NOT NULL,
    variety VARCHAR(100),  -- "Pioneer 1234", "OSSK 602", etc.
    planting_date DATE,
    expected_harvest_date DATE,
    actual_harvest_date DATE,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'harvested', 'failed')),
    yield_per_hectare DECIMAL(8, 2),  -- kg/ha or t/ha
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- AVA conversations - chat history with farmers
CREATE TABLE ava_conversations (
    id SERIAL PRIMARY KEY,
    farmer_id INTEGER REFERENCES ava_farmers(id) ON DELETE SET NULL,
    wa_phone_number VARCHAR(20),  -- For WhatsApp integration
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    language VARCHAR(5) DEFAULT 'hr',  -- 'hr' for Croatian
    topic VARCHAR(50),  -- 'pest_control', 'fertilization', 'weather', etc.
    confidence_score DECIMAL(3, 2)  -- AI confidence in answer (0-1)
);

-- Weather data for agricultural planning
CREATE TABLE ava_weather (
    id SERIAL PRIMARY KEY,
    location VARCHAR(100) NOT NULL,
    date DATE NOT NULL,
    temperature_min DECIMAL(4, 1),  -- Celsius
    temperature_max DECIMAL(4, 1),  -- Celsius
    humidity DECIMAL(5, 2),  -- Percentage
    rainfall DECIMAL(6, 2),  -- mm
    wind_speed DECIMAL(5, 2),  -- km/h
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Agricultural advice and recommendations
CREATE TABLE ava_recommendations (
    id SERIAL PRIMARY KEY,
    farmer_id INTEGER REFERENCES ava_farmers(id) ON DELETE CASCADE,
    field_id INTEGER REFERENCES ava_fields(field_id) ON DELETE CASCADE,
    recommendation_type VARCHAR(50),  -- 'fertilization', 'pest_control', 'irrigation'
    recommendation_text TEXT NOT NULL,
    priority VARCHAR(10) DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'urgent')),
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'implemented', 'ignored')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    valid_until DATE
);

-- Farm tasks table for agricultural operations logging
CREATE TABLE farm_tasks (
    id SERIAL PRIMARY KEY,
    farmer_id INTEGER REFERENCES ava_farmers(id) ON DELETE CASCADE,
    field_id INTEGER REFERENCES ava_fields(field_id) ON DELETE SET NULL,
    task_type VARCHAR(50) NOT NULL,  -- 'planting', 'fertilization', 'spraying', 'harvest'
    task_description TEXT NOT NULL,
    task_date DATE DEFAULT CURRENT_DATE,
    status VARCHAR(20) DEFAULT 'completed' CHECK (status IN ('planned', 'in_progress', 'completed', 'cancelled')),
    cost DECIMAL(10, 2),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- LLM debug log for monitoring AI operations
CREATE TABLE llm_debug_log (
    id SERIAL PRIMARY KEY,
    operation_type VARCHAR(50) NOT NULL,  -- 'query', 'routing', 'translation'
    input_text TEXT,
    output_text TEXT,
    model_used VARCHAR(50),
    tokens_used INTEGER,
    latency_ms INTEGER,
    success BOOLEAN NOT NULL,
    error_message TEXT,
    farmer_id INTEGER REFERENCES ava_farmers(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- System health monitoring
CREATE TABLE system_health_log (
    id SERIAL PRIMARY KEY,
    component_name VARCHAR(50) NOT NULL,  -- 'database', 'knowledge_base', 'external_api'
    status VARCHAR(20) NOT NULL CHECK (status IN ('healthy', 'degraded', 'unhealthy')),
    response_time_ms INTEGER,
    error_message TEXT,
    metadata JSONB,
    checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert sample Croatian crops
INSERT INTO ava_crops (crop_name, crop_type, typical_cycle_days, croatian_name, description) VALUES
('Corn', 'grain', 120, 'Kukuruz', 'Main grain crop in Croatia'),
('Wheat', 'grain', 200, 'Pšenica', 'Winter wheat commonly grown'),
('Barley', 'grain', 180, 'Ječam', 'Used for animal feed and brewing'),
('Sunflower', 'oilseed', 110, 'Suncokret', 'Oil crop, popular in eastern Croatia'),
('Soybean', 'legume', 130, 'Soja', 'Protein crop, nitrogen-fixing'),
('Sugar Beet', 'industrial', 180, 'Šećerna repa', 'Industrial crop for sugar production'),
('Potato', 'vegetable', 90, 'Krumpir', 'Staple vegetable crop'),
('Tomato', 'vegetable', 80, 'Rajčica', 'Popular greenhouse and field crop'),
('Cabbage', 'vegetable', 120, 'Kupus', 'Traditional Croatian vegetable'),
('Apple', 'fruit', 365, 'Jabuka', 'Common fruit crop in northern Croatia'),
('Grape', 'fruit', 365, 'Grožđe', 'Wine and table grapes'),
('Alfalfa', 'forage', 365, 'Lucerna', 'Perennial forage crop for livestock');

-- Create indexes for better performance
CREATE INDEX idx_ava_farmers_wa_phone ON ava_farmers(wa_phone_number);
CREATE INDEX idx_ava_conversations_farmer_id ON ava_conversations(farmer_id);
CREATE INDEX idx_ava_conversations_created_at ON ava_conversations(created_at);
CREATE INDEX idx_ava_field_crops_field_id ON ava_field_crops(field_id);
CREATE INDEX idx_ava_weather_location_date ON ava_weather(location, date);
CREATE INDEX idx_ava_recommendations_farmer_id ON ava_recommendations(farmer_id);
CREATE INDEX idx_farm_tasks_farmer_id ON farm_tasks(farmer_id);
CREATE INDEX idx_farm_tasks_date ON farm_tasks(task_date);
CREATE INDEX idx_farm_tasks_type ON farm_tasks(task_type);
CREATE INDEX idx_llm_debug_created_at ON llm_debug_log(created_at);
CREATE INDEX idx_llm_debug_operation ON llm_debug_log(operation_type);
CREATE INDEX idx_system_health_component ON system_health_log(component_name, checked_at);

-- Views for common queries
CREATE VIEW farmer_summary AS
SELECT 
    f.id,
    f.farm_name,
    f.manager_name,
    f.manager_last_name,
    f.total_hectares,
    f.farmer_type,
    COUNT(DISTINCT fld.field_id) as field_count,
    COUNT(DISTINCT conv.id) as conversation_count,
    COUNT(DISTINCT ft.id) as task_count
FROM ava_farmers f
LEFT JOIN ava_fields fld ON f.id = fld.farmer_id
LEFT JOIN ava_conversations conv ON f.id = conv.farmer_id
LEFT JOIN farm_tasks ft ON f.id = ft.farmer_id
GROUP BY f.id, f.farm_name, f.manager_name, f.manager_last_name, f.total_hectares, f.farmer_type;

CREATE VIEW active_crops AS
SELECT 
    fc.id,
    f.farm_name,
    fld.field_name,
    fc.crop_name,
    fc.variety,
    fc.planting_date,
    fc.expected_harvest_date,
    c.croatian_name,
    c.crop_type
FROM ava_field_crops fc
JOIN ava_fields fld ON fc.field_id = fld.field_id
JOIN ava_farmers f ON fld.farmer_id = f.id
LEFT JOIN ava_crops c ON fc.crop_name = c.crop_name
WHERE fc.status = 'active';

-- View for system monitoring
CREATE VIEW system_status AS
SELECT 
    component_name,
    status,
    AVG(response_time_ms) as avg_response_time,
    COUNT(*) as check_count,
    MAX(checked_at) as last_check
FROM system_health_log 
WHERE checked_at > CURRENT_TIMESTAMP - INTERVAL '24 hours'
GROUP BY component_name, status
ORDER BY component_name;