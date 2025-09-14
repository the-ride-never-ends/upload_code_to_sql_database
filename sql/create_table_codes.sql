CREATE TABLE IF NOT EXISTS codes (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    cid VARCHAR(255) UNIQUE NOT NULL, -- Made on insert (from computer_code, signature, docstring), immutable
    version_cid VARCHAR(255) NOT NULL, -- Updates on changes
    signature TEXT DEFAULT NULL,
    docstring TEXT DEFAULT NULL,
    computer_code TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_version_cid (version_cid)
);