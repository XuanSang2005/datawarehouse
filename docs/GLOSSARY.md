# Glossary

Data warehouse terms used in the project, with short definitions and concrete examples from the repo.

## Architecture

| Term | Definition | In this project |
|---|---|---|
| **OLTP** | Operational system that writes/updates individual transactions | The booking software (PMS). The CSV file is data extracted from it |
| **OLAP** | Analytical system that aggregates large volumes of data | The gold layer + dashboards |
| **Data Warehouse** | Store of clean, integrated, subject-oriented, time-variant data | The `gold` schema |
| **Data Lake** | Store of raw data in any format | `data/raw/` + the `bronze` schema |
| **Lakehouse** | Combines a lake (raw, cheap) with a warehouse (structured) | The whole system |
| **Medallion architecture** | Three layers: Bronze (raw) → Silver (clean) → Gold (analysis-ready) | `database/bronze`, `silver`, `gold` |
| **Data Mart** | A subset of the DW serving one department | The `kpi_*` tables for Revenue / Marketing |

## ETL

| Term | Definition | In this project |
|---|---|---|
| **Extract** | Retrieve data from a source | `etl/extract/` |
| **Load** | Load data into the store | `etl/load/bronze_loader.py` (COPY) |
| **Transform** | Clean and reshape data | `database/silver/*.sql`, `database/gold/*.sql` |
| **ELT** | Load raw data first, transform inside the DB afterwards | The approach used by this project |
| **Full load / Incremental load** | Reload everything / load only new data | Full load is used |
| **Data quality check** | Detect anomalous data | `database/checks/` |
| **Data lineage** | Trace where a number comes from | `_source_row` in bronze = `booking_id` in silver |
| **Orchestration** | Control the order of the steps | `etl/run_pipeline.py` |

## Dimensional modeling

| Term | Definition | Example |
|---|---|---|
| **Fact table** | Table of events that holds the measures | `fact_booking` |
| **Dimension table** | Context table: who, when, where, through which channel | `dim_date`, `dim_hotel`, `dim_country` |
| **Grain** | What one fact row represents | 1 booking; or 1 hotel × 1 night |
| **Measure** | Numeric column in a fact table | `revenue`, `total_nights`, `adr` |
| **Additive measure** | Can be summed across every dimension | `revenue`, `room_nights` |
| **Semi-additive measure** | Cannot be summed across time | Number of occupied rooms per day |
| **Non-additive measure** | Cannot be summed; must be recomputed from its components | **ADR**, **cancellation rate** |
| **Natural key** | Identifier from the source system | `country = 'PRT'` |
| **Surrogate key** | Integer key generated inside the DW | `country_key = 17` |
| **Star schema** | Fact table in the center, dimensions joined directly to it | The gold model |
| **Snowflake schema** | Dimensions normalized into several tables | Not used |
| **Hierarchy** | Levels within a dimension | Year → Quarter → Month → Week → Day |
| **Role-playing dimension** | One dimension used in several roles | `dim_date` for booking date and arrival date |
| **Degenerate dimension** | Identifier stored in the fact table without its own table | `booking_id` |
| **Junk dimension** | Groups miscellaneous low-cardinality flags into one table | `dim_booking_profile` (meal, deposit_type, customer_type) |
| **Conformed dimension** | Dimension shared by several fact tables | `dim_date`, `dim_hotel` |
| **SCD Type 1 / Type 2** | Handling changing attributes: overwrite / add a new row and keep history | Designed for `dim_agent` |
| **Transaction fact** | Each row is one event | `fact_booking` |
| **Periodic snapshot** | State captured at regular intervals | `fact_daily_occupancy` |
| **Accumulating snapshot** | Tracks a lifecycle through several milestones | Booked → cancelled/arrived → checked out |

## OLAP operations

| Operation | Definition | Example |
|---|---|---|
| **Roll-up** | Aggregate to a higher level | Month → Year |
| **Drill-down** | Move down to more detail | Year → Month → Week |
| **Slice** | Fix one dimension | City Hotel only |
| **Dice** | Filter on several dimensions | City Hotel + OTA + 2016 |
| **Pivot** | Rotate the axes | Swap rows and columns |

## Hotel KPIs

| KPI | Formula |
|---|---|
| **Room-nights** | `weekend_nights + week_nights` |
| **Revenue** | `adr × total_nights` (non-cancelled bookings only) |
| **ADR** (Average Daily Rate) | `sum(revenue) / sum(room_nights)` |
| **Cancellation rate** | `cancelled bookings / total bookings` |
| **Lead time** | Number of days from booking to arrival |
| **LOS** (Length of Stay) | Average number of nights per stay |
| **Occupancy** | `room_nights sold / room_nights available` (requires capacity input) |
| **RevPAR** (Revenue per Available Room) | `revenue / room_nights available` (requires capacity input) |

## Decision support

| Term | Definition |
|---|---|
| **DSS** | Decision Support System |
| **Descriptive / Diagnostic / Predictive / Prescriptive** | What happened / why it happened / what will happen / what should be done |
| **What-if analysis** | Simulating outcomes under parameter scenarios |
| **Data leakage** | The model gets to see the answer in advance (e.g. by using `reservation_status`) |
| **Time-based split** | Train on earlier periods and test on later ones, as in real deployment |
| **AUC, Precision, Recall** | Metrics for classification models (cancellation prediction) |
| **MAPE** | Mean absolute percentage error (forecast evaluation) |
