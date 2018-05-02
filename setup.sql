CREATE DATABASE IF NOT EXISTS leakScraper;
USE leakScraper;
CREATE TABLE IF NOT EXISTS leaks (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    name varchar(255) NOT NULL,
    imported BIGINT,
    filename varchar(255) NOT NULL);

CREATE TABLE IF NOT EXISTS credentials (
    id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    prefix VARCHAR(255) NOT NULL,
    domain VARCHAR(255) NOT NULL,
    hash VARCHAR(512) NOT NULL,
    plain VARCHAR(512) NOT NULL,
    leak INT NOT NULL,
    FOREIGN KEY (leak) REFERENCES leaks(id) ON DELETE CASCADE) ENGINE=INNODB;

    CREATE INDEX leak_index ON credentials (leak) USING HASH;
    CREATE INDEX domain_index ON credentials (domain) USING HASH;