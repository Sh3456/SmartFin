-- SmartFin Fintech Fraud Analytics — MySQL 8.0+
-- This script is for MySQL Workbench. It is NOT Oracle SQL.
CREATE DATABASE IF NOT EXISTS smartfin_fraud_analytics
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE smartfin_fraud_analytics;

CREATE TABLE IF NOT EXISTS locations (
    location_id VARCHAR(50) PRIMARY KEY,
    country VARCHAR(100),
    region_state VARCHAR(100),
    city VARCHAR(100),
    zip_code VARCHAR(20),
    risk_score DECIMAL(5,2),
    created_at DATETIME,
    CONSTRAINT chk_locations_risk CHECK (risk_score IS NULL OR risk_score BETWEEN 0 AND 100)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS devices (
    device_id VARCHAR(50) PRIMARY KEY,
    device_type VARCHAR(50),
    os_name VARCHAR(50),
    browser VARCHAR(50),
    ip_address VARCHAR(45),
    is_vpn_proxy VARCHAR(5),
    location_id VARCHAR(50),
    first_seen_at DATETIME,
    CONSTRAINT fk_devices_location FOREIGN KEY (location_id) REFERENCES locations(location_id),
    CONSTRAINT chk_devices_vpn CHECK (is_vpn_proxy IS NULL OR LOWER(is_vpn_proxy) IN ('true','false','1','0','yes','no')),
    INDEX idx_devices_ip (ip_address),
    INDEX idx_devices_location (location_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS customers (
    customer_id VARCHAR(50) PRIMARY KEY,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    email VARCHAR(255) UNIQUE,
    phone_number VARCHAR(20),
    account_status VARCHAR(20),
    kyc_verified VARCHAR(5),
    account_created_at DATETIME,
    primary_location_id VARCHAR(50),
    CONSTRAINT fk_customers_location FOREIGN KEY (primary_location_id) REFERENCES locations(location_id),
    CONSTRAINT chk_customers_kyc CHECK (kyc_verified IS NULL OR LOWER(kyc_verified) IN ('true','false','1','0','yes','no')),
    INDEX idx_customers_location (primary_location_id),
    INDEX idx_customers_kyc (kyc_verified)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS merchants (
    merchant_id VARCHAR(50) PRIMARY KEY,
    merchant_name VARCHAR(255),
    mcc_code VARCHAR(4),
    mcc_description VARCHAR(100),
    business_type VARCHAR(50),
    risk_tier VARCHAR(20),
    onboarding_date DATE,
    primary_location_id VARCHAR(50),
    CONSTRAINT fk_merchants_location FOREIGN KEY (primary_location_id) REFERENCES locations(location_id),
    INDEX idx_merchants_location (primary_location_id),
    INDEX idx_merchants_risk_tier (risk_tier)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS transactions (
    transaction_id VARCHAR(50) PRIMARY KEY,
    customer_id VARCHAR(50),
    merchant_id VARCHAR(50),
    device_id VARCHAR(50),
    amount DECIMAL(15,2) NOT NULL,
    currency VARCHAR(3),
    transaction_timestamp DATETIME NOT NULL,
    status VARCHAR(20),
    payment_method VARCHAR(50),
    card_network VARCHAR(20),
    cvv_match VARCHAR(5),
    avs_match VARCHAR(5),
    CONSTRAINT fk_transactions_customer FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    CONSTRAINT fk_transactions_merchant FOREIGN KEY (merchant_id) REFERENCES merchants(merchant_id),
    CONSTRAINT fk_transactions_device FOREIGN KEY (device_id) REFERENCES devices(device_id),
    CONSTRAINT chk_transactions_amount CHECK (amount >= 0),
    CONSTRAINT chk_transactions_cvv CHECK (cvv_match IS NULL OR LOWER(cvv_match) IN ('true','false','1','0','yes','no')),
    CONSTRAINT chk_transactions_avs CHECK (avs_match IS NULL OR LOWER(avs_match) IN ('true','false','1','0','yes','no')),
    INDEX idx_transactions_customer_time (customer_id, transaction_timestamp),
    INDEX idx_transactions_merchant (merchant_id),
    INDEX idx_transactions_device (device_id),
    INDEX idx_transactions_time_status (transaction_timestamp, status)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS chargebacks (
    chargeback_id VARCHAR(50) PRIMARY KEY,
    transaction_id VARCHAR(50) NOT NULL,
    chargeback_date DATETIME,
    reason_code VARCHAR(50),
    chargeback_amount DECIMAL(15,2) NOT NULL,
    status VARCHAR(20),
    CONSTRAINT fk_chargebacks_transaction FOREIGN KEY (transaction_id) REFERENCES transactions(transaction_id),
    CONSTRAINT chk_chargebacks_amount CHECK (chargeback_amount >= 0),
    INDEX idx_chargebacks_transaction (transaction_id),
    INDEX idx_chargebacks_date_status (chargeback_date, status)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS fraud_alerts (
    alert_id VARCHAR(50) PRIMARY KEY,
    transaction_id VARCHAR(50) NOT NULL,
    alert_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    rule_triggered VARCHAR(100) NOT NULL,
    risk_score INT NOT NULL,
    reviewer_status VARCHAR(20) DEFAULT 'Unassigned',
    resolution VARCHAR(50) DEFAULT 'Unresolved',
    CONSTRAINT fk_fraud_alerts_transaction FOREIGN KEY (transaction_id) REFERENCES transactions(transaction_id),
    CONSTRAINT chk_fraud_alerts_score CHECK (risk_score BETWEEN 0 AND 100),
    INDEX idx_fraud_alerts_status (reviewer_status),
    INDEX idx_fraud_alerts_rule (rule_triggered),
    INDEX idx_fraud_alerts_transaction_rule (transaction_id, rule_triggered)
) ENGINE=InnoDB;

-- Confirm the target schema and table count after the script completes.
SELECT DATABASE() AS active_database;
SELECT COUNT(*) AS created_tables
FROM information_schema.tables
WHERE table_schema = DATABASE() AND table_type = 'BASE TABLE';
