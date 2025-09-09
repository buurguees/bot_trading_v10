-- init.sql - Schema inicial de TimescaleDB
-- Ubicación: C:\TradingBot_v10\docker\timescaledb\init.sql

-- Crear extensión TimescaleDB
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- Crear usuario y base de datos si no existen
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'trading_bot') THEN
        CREATE ROLE trading_bot LOGIN PASSWORD 'trading_bot_password';
    END IF;
END
$$;

-- Otorgar permisos
GRANT ALL PRIVILEGES ON DATABASE trading_bot_enterprise TO trading_bot;
ALTER USER trading_bot CREATEDB;

-- Tabla principal de ticks de mercado
CREATE TABLE IF NOT EXISTS market_ticks (
    time TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    price DECIMAL(18, 8) NOT NULL,
    volume DECIMAL(18, 8) NOT NULL,
    bid DECIMAL(18, 8),
    ask DECIMAL(18, 8),
    bid_size DECIMAL(18, 8),
    ask_size DECIMAL(18, 8),
    exchange VARCHAR(20) DEFAULT 'bitget',
    tick_id BIGSERIAL,
    raw_data JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (time, symbol)
);

-- Convertir a hypertable
SELECT create_hypertable('market_ticks', 'time', if_not_exists => TRUE);

-- Índices para mejor performance
CREATE INDEX IF NOT EXISTS idx_market_ticks_symbol_time ON market_ticks (symbol, time DESC);
CREATE INDEX IF NOT EXISTS idx_market_ticks_price ON market_ticks (symbol, price);
CREATE INDEX IF NOT EXISTS idx_market_ticks_volume ON market_ticks (symbol, volume);

-- Tabla de datos procesados (OHLCV)
CREATE TABLE IF NOT EXISTS ohlcv_data (
    time TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    open DECIMAL(18, 8) NOT NULL,
    high DECIMAL(18, 8) NOT NULL,
    low DECIMAL(18, 8) NOT NULL,
    close DECIMAL(18, 8) NOT NULL,
    volume DECIMAL(18, 8) NOT NULL,
    trades_count INTEGER,
    vwap DECIMAL(18, 8),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (time, symbol, timeframe)
);

-- Convertir a hypertable
SELECT create_hypertable('ohlcv_data', 'time', if_not_exists => TRUE);

-- Índices para OHLCV
CREATE INDEX IF NOT EXISTS idx_ohlcv_symbol_timeframe_time ON ohlcv_data (symbol, timeframe, time DESC);

-- Tabla de features técnicos
CREATE TABLE IF NOT EXISTS technical_features (
    time TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    sma_10 DECIMAL(18, 8),
    sma_20 DECIMAL(18, 8),
    ema_12 DECIMAL(18, 8),
    ema_26 DECIMAL(18, 8),
    rsi_14 DECIMAL(8, 4),
    macd DECIMAL(18, 8),
    macd_signal DECIMAL(18, 8),
    macd_histogram DECIMAL(18, 8),
    bollinger_upper DECIMAL(18, 8),
    bollinger_lower DECIMAL(18, 8),
    bollinger_middle DECIMAL(18, 8),
    atr_14 DECIMAL(18, 8),
    volume_sma_10 DECIMAL(18, 8),
    vwap DECIMAL(18, 8),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (time, symbol, timeframe)
);

-- Convertir a hypertable
SELECT create_hypertable('technical_features', 'time', if_not_exists => TRUE);

-- Tabla de predicciones del modelo
CREATE TABLE IF NOT EXISTS model_predictions (
    time TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    model_name VARCHAR(50) NOT NULL,
    prediction_type VARCHAR(20) NOT NULL, -- 'classification', 'regression'
    prediction_value DECIMAL(8, 6),
    confidence DECIMAL(6, 4),
    probabilities JSONB, -- [sell_prob, hold_prob, buy_prob]
    features_used JSONB,
    model_version VARCHAR(20),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (time, symbol, model_name)
);

-- Convertir a hypertable
SELECT create_hypertable('model_predictions', 'time', if_not_exists => TRUE);

-- Tabla de trades ejecutados
CREATE TABLE IF NOT EXISTS executed_trades (
    id BIGSERIAL PRIMARY KEY,
    time TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL, -- 'buy', 'sell'
    order_type VARCHAR(20) NOT NULL, -- 'market', 'limit', 'stop'
    amount DECIMAL(18, 8) NOT NULL,
    price DECIMAL(18, 8) NOT NULL,
    filled_amount DECIMAL(18, 8),
    filled_price DECIMAL(18, 8),
    commission DECIMAL(18, 8),
    commission_asset VARCHAR(20),
    order_id VARCHAR(100),
    trade_id VARCHAR(100),
    status VARCHAR(20), -- 'filled', 'partial', 'cancelled'
    leverage INTEGER DEFAULT 1,
    position_side VARCHAR(10), -- 'long', 'short'
    pnl DECIMAL(18, 8),
    pnl_pct DECIMAL(8, 4),
    prediction_id BIGINT,
    strategy_name VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Índices para trades
CREATE INDEX IF NOT EXISTS idx_executed_trades_time ON executed_trades (time DESC);
CREATE INDEX IF NOT EXISTS idx_executed_trades_symbol ON executed_trades (symbol, time DESC);
CREATE INDEX IF NOT EXISTS idx_executed_trades_strategy ON executed_trades (strategy_name, time DESC);

-- Tabla de métricas de rendimiento
CREATE TABLE IF NOT EXISTS performance_metrics (
    time TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(20),
    timeframe VARCHAR(10),
    metric_name VARCHAR(50) NOT NULL,
    metric_value DECIMAL(18, 8) NOT NULL,
    metric_type VARCHAR(20), -- 'gauge', 'counter', 'histogram'
    labels JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (time, metric_name, symbol)
);

-- Convertir a hypertable
SELECT create_hypertable('performance_metrics', 'time', if_not_exists => TRUE);

-- Políticas de compresión para optimizar almacenamiento
SELECT add_compression_policy('market_ticks', INTERVAL '7 days');
SELECT add_compression_policy('ohlcv_data', INTERVAL '3 days');
SELECT add_compression_policy('technical_features', INTERVAL '1 day');
SELECT add_compression_policy('model_predictions', INTERVAL '1 day');
SELECT add_compression_policy('performance_metrics', INTERVAL '1 day');

-- Políticas de retención para gestión automática de datos
SELECT add_retention_policy('market_ticks', INTERVAL '30 days');
SELECT add_retention_policy('ohlcv_data', INTERVAL '90 days');
SELECT add_retention_policy('technical_features', INTERVAL '60 days');
SELECT add_retention_policy('model_predictions', INTERVAL '30 days');
SELECT add_retention_policy('performance_metrics', INTERVAL '90 days');

-- Vistas útiles para análisis
CREATE OR REPLACE VIEW latest_market_data AS
SELECT DISTINCT ON (symbol)
    symbol,
    time,
    price,
    volume,
    bid,
    ask
FROM market_ticks
ORDER BY symbol, time DESC;

CREATE OR REPLACE VIEW daily_trading_summary AS
SELECT 
    DATE(time) as date,
    symbol,
    COUNT(*) as trades_count,
    SUM(amount) as total_volume,
    AVG(price) as avg_price,
    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
    SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losing_trades,
    SUM(pnl) as total_pnl,
    AVG(pnl) as avg_pnl
FROM executed_trades
WHERE time >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(time), symbol
ORDER BY date DESC, symbol;

-- Función para limpieza automática de datos antiguos
CREATE OR REPLACE FUNCTION cleanup_old_data()
RETURNS void AS $$
BEGIN
    -- Limpiar datos de market_ticks más antiguos de 30 días
    DELETE FROM market_ticks WHERE time < NOW() - INTERVAL '30 days';
    
    -- Limpiar datos de technical_features más antiguos de 60 días
    DELETE FROM technical_features WHERE time < NOW() - INTERVAL '60 days';
    
    -- Limpiar datos de model_predictions más antiguos de 30 días
    DELETE FROM model_predictions WHERE time < NOW() - INTERVAL '30 days';
    
    -- Log de limpieza
    INSERT INTO performance_metrics (time, metric_name, metric_value, metric_type)
    VALUES (NOW(), 'cleanup_executed', 1, 'counter');
    
    RAISE NOTICE 'Limpieza de datos antiguos completada';
END;
$$ LANGUAGE plpgsql;

-- Crear job de limpieza automática (requiere pg_cron)
-- SELECT cron.schedule('cleanup-old-data', '0 2 * * *', 'SELECT cleanup_old_data();');
