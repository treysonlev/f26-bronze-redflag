-- =====================================================================
-- RedFlag database schema
-- Target: PostgreSQL 16 (redflag-db container)
-- Matches the RedFlag ERD and stores extension findings:
-- SOURCE, VERDICT, CLAIM, KEYWORD, FINDING
-- ERD can be found here: 
-- https://docs.google.com/document/d/1NLMD_OJMcnHvp8xkk-Pcyw1ucdz-jwNKqNE4qK6Zux8/edit?tab=t.0
-- 
-- Run with:
--   docker exec -i redflag-db psql -U redflag -d redflag < ./init/01_schema.sql
-- =====================================================================

-- BEGIN and COMMIT statements create a database transaction block, ensuring 
-- everything fails or everything succeeds
BEGIN; 

-- Uncomment to rebuild from scratch. WARNING: deletes all existing data. (run in psql)
-- DROP TABLE IF EXISTS claims, keyword, claim, verdict, source CASCADE;

-- ---------------------------------------------------------------------
-- SOURCE: a webpage excerpt used as evidence for exactly one verdict.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS source (
    source_id       INTEGER GENERATED ALWAYS AS IDENTITY,
    url             VARCHAR(2048) NOT NULL,
    excerpt         VARCHAR(2048) NOT NULL,
    date_collected  TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_source PRIMARY KEY (source_id)
);

-- ---------------------------------------------------------------------
-- VERDICT: the LLM's evaluation of one claim against one source.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS verdict (
    verdict_id   INTEGER GENERATED ALWAYS AS IDENTITY,
    source_id    INTEGER       NOT NULL,
    verdict      BOOLEAN       NOT NULL,
    explanation  VARCHAR(2048) NOT NULL,
    correctness  DECIMAL(3,2)  NOT NULL,
    confidence   DECIMAL(3,2)  NOT NULL,
    "timestamp"  TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_verdict PRIMARY KEY (verdict_id),
    -- One source per verdict, and one verdict per source (1:1).
    CONSTRAINT fk_verdict_source FOREIGN KEY (source_id)
        REFERENCES source (source_id) ON DELETE RESTRICT,
    CONSTRAINT uq_verdict_source UNIQUE (source_id),
    -- Scores range from 0.00 to 1.00.
    CONSTRAINT ck_verdict_correctness CHECK (correctness BETWEEN 0 AND 1),
    CONSTRAINT ck_verdict_confidence  CHECK (confidence  BETWEEN 0 AND 1)
);

-- ---------------------------------------------------------------------
-- CLAIM: a factual assertion extracted from page text.
-- verdict_id is NULL until the claim has been verified.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS claim (
    claim_id    INTEGER GENERATED ALWAYS AS IDENTITY,
    claim       VARCHAR(255) NOT NULL,
    verdict_id  INTEGER      NULL,

    CONSTRAINT pk_claim PRIMARY KEY (claim_id),
    -- Zero or one verdict per claim; a verdict belongs to one claim (1:1).
    CONSTRAINT fk_claim_verdict FOREIGN KEY (verdict_id)
        REFERENCES verdict (verdict_id) ON DELETE SET NULL,
    CONSTRAINT uq_claim_verdict UNIQUE (verdict_id)
);

-- ---------------------------------------------------------------------
-- FINDING: a result displayed by the extension. A finding can optionally
-- link to a factual claim; heuristic signals need not have a claim/verdict.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS finding (
    finding_id    INTEGER GENERATED ALWAYS AS IDENTITY,
    claim_id      INTEGER      NULL,
    matched_text  TEXT         NOT NULL,
    label         VARCHAR(120) NOT NULL,
    reason        VARCHAR(600) NOT NULL,
    flagtype      VARCHAR(20)  NOT NULL,
    result        VARCHAR(20)  NOT NULL DEFAULT 'unable_to_verify',
    "timestamp"   TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_finding PRIMARY KEY (finding_id),
    CONSTRAINT fk_finding_claim FOREIGN KEY (claim_id)
        REFERENCES claim (claim_id) ON DELETE SET NULL,
    CONSTRAINT ck_finding_flagtype
        CHECK (flagtype IN ('redflag', 'biasstar', 'signal')),
    CONSTRAINT ck_finding_result
        CHECK (result IN ('true', 'false', 'unable_to_verify'))
);

-- ---------------------------------------------------------------------
-- KEYWORD: a search term that identifies one claim during retrieval.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS keyword (
    keyword_id  INTEGER GENERATED ALWAYS AS IDENTITY,
    claim_id    INTEGER     NOT NULL,
    keyword     VARCHAR(50) NOT NULL,

    CONSTRAINT pk_keyword PRIMARY KEY (keyword_id),
    -- Many keywords per claim; deleting a claim deletes its keywords.
    CONSTRAINT fk_keyword_claim FOREIGN KEY (claim_id)
        REFERENCES claim (claim_id) ON DELETE CASCADE
);

-- Speeds up retrieval, which looks up claims by keyword.
CREATE INDEX IF NOT EXISTS idx_keyword_keyword  ON keyword (LOWER(keyword));
CREATE INDEX IF NOT EXISTS idx_keyword_claim_id ON keyword (claim_id);
CREATE INDEX IF NOT EXISTS idx_finding_claim_id ON finding (claim_id);

-- ---------------------------------------------------------------------
-- Rules the backend must enforce (foreign keys cannot require these):
--   * Every CLAIM has at least one KEYWORD.
--   * Every SOURCE is referenced by exactly one VERDICT.
--   * Every VERDICT is referenced by exactly one CLAIM.
-- Insert SOURCE -> VERDICT -> update CLAIM.verdict_id in one transaction.
-- ---------------------------------------------------------------------

COMMIT;
