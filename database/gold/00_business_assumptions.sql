-- =============================================================================
-- gold.business_assumptions — Business assumption parameters that the dataset does not have.
-- Source: set by the team (see docs/STAR_SCHEMA.md, section 9)
-- Grain : 1 row = 1 parameter
-- Facts and views read the DEFAULT values here. The what-if page lets the user enter other values
-- (the backend recomputes from the base columns and does not write to this table).
-- To change a default: edit this file, then run `python -m etl.run_pipeline --from gold`.
-- =============================================================================

DROP TABLE IF EXISTS gold.business_assumptions CASCADE;

CREATE TABLE gold.business_assumptions (
    param_name   TEXT PRIMARY KEY,
    param_value  NUMERIC(10, 4) NOT NULL,
    unit         TEXT NOT NULL,
    description  TEXT NOT NULL
);

INSERT INTO gold.business_assumptions (param_name, param_value, unit, description) VALUES
    ('non_refund_deposit_rate', 0.20, 'ratio',
     'Share of booked_revenue the hotel retains as deposit when a Non Refund booking is canceled. '
     'The dataset has no actual deposit amounts, so this is an assumption.');
