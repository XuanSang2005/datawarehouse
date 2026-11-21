# ml/: Predictive analytics

Data exploration and modelling. **Results for the application are written to the `gold.ml_*` tables**;
the backend only reads those tables and never trains a model.

```
ml/
├── notebooks/       Exploration (EDA), experiments: NN_<name>_<topic>.ipynb, clear outputs before committing
├── models/          Trained model files (.joblib), NOT committed
├── tests/           pytest, no DB needed (test_cancellation_*.py, test_forecast_*.py)
├── cancellation/    Cancellation prediction model → gold.ml_booking_risk (E3, see the section below)
└── forecast/        Weekly demand forecast → gold.ml_demand_forecast (E4, see the section below)
```

Reading data: use `etl.db.connect()` to read from `silver` or `gold`.

## Mandatory notes
- ⛔ **Data leakage**: do not use `reservation_status`, `reservation_status_date`. Consider dropping `assigned_room_type`, `booking_changes`, `days_in_waiting_list` (information that may arise after booking time). The cancellation model (E3) drops all 5 of these columns plus `required_car_parking_spaces`: see "Dropped columns and why".
- Split train/test **by time** (e.g. train: up to the end of 2016, test: 2017), never randomly.
- Record the metrics below for the **Evaluation** chapter of the report.

## Cancellation prediction model (E3): `ml/cancellation/`

```bash
python -m ml.cancellation.train                # train + evaluate + write gold.ml_booking_risk, gold.ml_model_metrics
python -m ml.cancellation.train --no-write     # train and print metrics only
pytest ml/tests                                # leakage and threshold tests (no DB needed)
```
Run from the repo root, with gold already built (`python -m etl.run_pipeline`). Takes about 1 minute.
If the machine is busy with other heavy work, set `OMP_NUM_THREADS=2` so HistGradientBoosting does not fight for CPU.

| File | Role |
|---|---|
| `database/ml/20_cancellation_eda.sql` | SELECT for the EDA notebook (silver, includes the leakage columns to prove the point) |
| `database/ml/21_cancellation_features.sql` | SELECT of the training/scoring data (gold.fact_booking + dimensions), WITHOUT leakage columns |
| `database/ml/02_ml_booking_risk.sql` | DDL of `gold.ml_booking_risk` (idempotent, the script runs it before writing) |
| `ml/cancellation/features.py` | Feature list, `LEAKAGE_COLUMNS` (dropped columns + reasons), time-based split |
| `ml/cancellation/evaluation.py` | Risk band threshold selection, metrics |
| `ml/cancellation/train.py` | Trains 2 models + a control model, permutation importance, scoring, DB writes |
| `ml/cancellation/store.py` | DB writes (deletes rows with the same `model_version`, then rewrites them, 1 transaction) |
| `ml/notebooks/01_claude_eda_cancellation.ipynb` | EDA: cancellation rate by hotel, lead time, channel, deposit, country, season; leakage columns |

Outputs: `gold.ml_booking_risk` (119,209 rows = all of `gold.fact_booking`, `model_version = cancellation_v1`),
`gold.ml_model_metrics` (100 rows, `model_name` starting with `cancellation_`), and in `ml/models/`:
`cancellation_gbm.joblib`, `cancellation_logreg.joblib`, `cancellation_report.json`, `cancellation_feature_importance.csv`.

### Data split
- **Train**: arrival_date < 2017-01-01 (78,590 bookings). **Test**: year 2017 (40,619 bookings, `is_test_set = TRUE`).
- **Validation** = last 6 months of train (2016-07 → 2016-12, 29,482 bookings): the model is fit on the earlier part of train
  and validation is used to choose hyperparameters and the risk band thresholds. The model is then refit on the full train set. The test set is never looked at while choosing.
- Scores of bookings in train (`is_test_set = FALSE`) are **in-sample** scores, more optimistic than reality; evaluation relies on test only.

### Features (29 columns: 13 categorical + 16 numeric, all known at booking time)
| Group | Features |
|---|---|
| Hotel, timing | `hotel_name`, `arrival_season` (High/Shoulder/Low), `arrival_day_of_week`, `arrival_is_holiday`, `booking_month` (booking month = month of arrival_date − lead_time) |
| Lead time, stay, guests | `lead_time`, `weekend_nights`, `week_nights`, `total_nights`, `adults`, `children`, `babies`, `party_type` |
| Channel | `market_segment`, `distribution_channel`, `agent_id`, `company_id` |
| Customer | `country_code` ⚠, `market_group` ⚠, `customer_type`, `is_repeated_guest`, `previous_cancellations`, `previous_bookings_not_canceled` |
| Booking | `deposit_type`, `meal`, `reserved_room_type`, `adr`, `adr_per_person` (adr / (adults + children)), `total_of_special_requests` |

Categories that appear < 100 times in train (rare agents, companies, countries) are merged into an "infrequent" group.

### Dropped columns and why
| Column | Reason |
|---|---|
| `reservation_status`, `reservation_status_date` (+ `status_date_key`) | ⛔ They are the outcome / cancellation date |
| `room_nights_sold`, `realized_revenue`, `lost_revenue`, `deposit_retained`, `net_lost_revenue`, `cancel_lead_days` | ⛔ Computed from `is_canceled` (header of `database/gold/30_fact_booking.sql`) |
| `assigned_room_type` (+ `is_room_changed`) | Assigned at check-in: bookings whose room was changed cancel only 5.4% (vs 41.6%) |
| `booking_changes` | Accumulates until check-in/cancellation: modified bookings cancel 15.7% vs 40.9% |
| `days_in_waiting_list` | Settled after the booking entry date, not reliably available at scoring time |
| `required_car_parking_spaces` | Of the 7,416 bookings with parking spaces (silver), **none canceled**: most likely recorded at check-in |
| `arrival_month`, `arrival_week` | Not leakage, but each month only has 2 years of data so the model memorizes each year: validation AUC 0.844 → 0.876 when dropped |
| `arrival_date`, arrival year | Only used for the split; the model cannot extrapolate to a new year |

`ml/tests/test_cancellation_features.py` asserts that none of the columns above is in the feature set and that
`21_cancellation_features.sql` selects none of them.

### Risk bands (chosen on validation)
| Band | Condition | Suggested action | Test 2017: bookings (share), actual cancellation rate |
|---|---|---|---|
| **High** | p ≥ **0.31** | Require a deposit / count toward the overbooking allowance | 15,988 (39%), 74.1% canceled |
| **Medium** | 0.17 ≤ p < 0.31 | Call to reconfirm, payment reminder | 6,304 (16%), 35.9% canceled |
| **Low** | p < 0.17 | No intervention needed | 18,327 (45%), 8.9% canceled |

- **High** = smallest threshold whose **precision on validation is ≥ 80%**: requiring a deposit or overbooking is an expensive action
  (lost customers, no rooms left) when wrong, so at least 4 out of 5 bookings labelled High must actually cancel.
- **Medium** = threshold that **maximizes F1** on validation: a wide net for a cheap action (a phone call), catching ~90% of cancellations.
- The thresholds are stored in `gold.ml_model_metrics` (`threshold_high`, `threshold_medium`, dataset `validation`)
  so the backend can display the band definitions.
- On test, High precision is 74% (below the 80% target on validation): 2017 has more cancellations (38.7% vs
  36.2% in train). Monitor this and re-choose the thresholds when new data arrives.

### Most important features (permutation importance on test, AUC drop when the column is shuffled)
| # | Feature | AUC drop |
|---|---|---|
| 1 | `agent_id` | 0.127 |
| 2 | `country_code` | 0.091 |
| 3 | `deposit_type` | 0.080 |
| 4 | `lead_time` | 0.042 |
| 5 | `total_of_special_requests` | 0.040 |
| 6 | `customer_type` | 0.019 |
| 7 | `previous_bookings_not_canceled` | 0.009 |
| 8 | `market_segment` | 0.004 |
| 9 | `previous_cancellations` | 0.003 |
| 10 | `booking_month` | 0.003 |

Interpretation note: `deposit_type = Non Refund` cancels 99% because these are mostly group bookings by agents who hold rooms and then cancel;
this is a correlation and does **not** mean that requiring a deposit makes guests cancel.

⚠ **Country**: PRT cancels 57% vs 24% for other countries. Nationality may only be confirmed at check-in
(canceled bookings keep the default value); if so, `country_code` carries part of the outcome. The control model without
`country_code` + `market_group` (`cancellation_gbm_no_country`) reaches test AUC **0.843**, below the 0.85 target.
The main model keeps country; presentations should state the AUC range 0.84–0.89 depending on this assumption.

## Evaluation results

**Cancellation prediction (E3)**: the test set is bookings arriving in 2017 (40,619 bookings, 38.7% cancellation rate). Precision/recall/F1 at the High threshold
of each model (chosen on validation). Main model: `cancellation_gbm`, `model_version = cancellation_v1`.
**Demand forecast (E4)**: rolling-origin backtest over the 2017 weeks, see the E4 section.

| Model | Test set | Metric | Result | Date |
|---|---|---|---|---|
| `cancellation_gbm` (HistGradientBoosting, main model) | 2017 | AUC | **0.888** (train 0.947, validation 0.881) | 2026-11-21 |
| | 2017 | PR-AUC / Brier | 0.843 / 0.138 | 2026-11-21 |
| | 2017 | High threshold | 0.31 (Medium 0.17) | 2026-11-21 |
| | 2017 | Precision / Recall / F1 (p ≥ 0.31) | 0.741 / 0.752 / 0.747 | 2026-11-21 |
| | 2017 | Precision / Recall / F1 (p ≥ 0.17, Medium + High) | 0.633 / 0.896 / 0.742 | 2026-11-21 |
| | 2017 | Confusion matrix (p ≥ 0.31) | TN 20,740, FP 4,145, FN 3,895, TP 11,839 | 2026-11-21 |
| `cancellation_logreg` (Logistic Regression, baseline) | 2017 | AUC | 0.871 (train 0.913, validation 0.868) | 2026-11-21 |
| | 2017 | PR-AUC / Brier | 0.828 / 0.144 | 2026-11-21 |
| | 2017 | High threshold | 0.42 (Medium 0.20) | 2026-11-21 |
| | 2017 | Precision / Recall / F1 (p ≥ 0.42) | 0.771 / 0.659 / 0.711 | 2026-11-21 |
| | 2017 | Confusion matrix (p ≥ 0.42) | TN 21,795, FP 3,090, FN 5,359, TP 10,375 | 2026-11-21 |
| `cancellation_gbm_no_country` (control, without country) | 2017 | AUC | 0.843 | 2026-11-21 |
| `forecast_gbm` (E4, main model) | Backtest 2017-01-02 → 2017-08-21, rolling origin h=1..8 | MAPE (h=1 / h=4 / h=8 / overall) | 6.5% / 7.2% / 11.8% / **8.6%** | 2026-11-21 |
| `forecast_seasonal_naive` (E4, baseline) | same as above | MAPE (h=1 / h=4 / h=8 / overall) | 11.6% / 11.6% / 11.6% / 11.6% | 2026-11-21 |
| `forecast_moving_avg` (E4, 4-week MA baseline) | same as above | MAPE (h=1 / h=4 / h=8 / overall) | 6.5% / 10.0% / 19.5% / 11.8% | 2026-11-21 |
| `forecast_gbm` (E4) | same as above | 80% interval coverage | 85.7% (seasonal naive 76.5%, MA 63.6%) | 2026-11-21 |

Conclusion: the main model meets goal G2 (AUC ≥ 0.85). Gradient Boosting beats the baseline by 0.016 AUC and has a higher F1.
Deep trees (63 leaves) give train AUC 0.99 but only 0.83 on validation (memorizing duplicated blocks of group bookings), so the model
uses shallow trees (7 leaves, at least 200 samples per leaf, 400 iterations, learning rate 0.05), chosen by validation AUC.

## E4: Weekly demand forecast

Forecasts **room-nights sold** (room-nights of non-canceled bookings) per hotel × week, for the
"Demand Forecast" page. Code: `ml/forecast/`; SQL: `database/ml/03_ml_demand_forecast.sql` (DDL),
`database/ml/31_forecast_weekly_series.sql` (weekly series SELECT).

```bash
python -m ml.forecast.train            # backtest + future forecast + DB writes (~1–3 minutes)
python -m ml.forecast.train --dry-run  # print the metrics table only, no DB writes
pytest ml/tests                        # unit tests (no DB needed)
```

The script can be re-run: it deletes the rows with its own `model_version` / `model_name` (`forecast_*`) and rewrites them,
without touching E3's rows in `gold.ml_model_metrics`.

### Data
- Source: `gold.fact_daily_occupancy` (sum of `rooms_occupied`) grouped by `gold.dim_date.week_start_date` (Monday).
- **Partial edge weeks are dropped**: 2015-06-29 (only 5 nights, from 07/01) and 2017-08-28 (only 4 nights, up to 08/31).
  Their totals are artificially low, so they are used neither for training nor as actuals; week 2017-08-28 is treated as the
  first future week (`actual_room_nights` = NULL). That leaves **112 complete 7-night weeks per hotel**
  (2015-07-06 → 2017-08-21), contiguous without gaps.
- "Same week last year" = 52 weeks back (364 days, same weekday). ISO year 2015 has 53 weeks, so this is off by at most 1 week
  from the ISO week number; acceptable.

### Models
| Model | How week origin+h is forecast |
|---|---|
| `forecast_seasonal_naive` | Value of the same week last year (t − 52) |
| `forecast_moving_avg` | Mean of the last 4 weeks, held flat for every h |
| `forecast_gbm` | `HistGradientBoostingRegressor` (scikit-learn) pooling both hotels, **recursive** forecast (the h=1 forecast is the lag for h=2…). Features: `is_resort`, `iso_week`, `n_holidays` (holidays in the week, `dim_date.is_holiday`), `lag_1`, `lag_2`, `ma_4`, `lag_52`, `seasonal_3` (mean of weeks t−51..t−53), `yoy_level` (ma_4 / ma_4 of the same period last year), `seasonal_adj` = `seasonal_3 × yoy_level`. Hyperparameters chosen up front (depth 3, 300 iterations, lr 0.05); only 3 configurations were compared on the calibration window (difference < 0.3 MAPE points), no tuning on the test set |

No SARIMA/Prophet: there are only 2 yearly cycles (~112 weeks), so a 52-week seasonal model would be very unstable;
GBM can use `lag_52` as an ordinary feature and pools both hotels for twice the samples. No new libraries added.

### Evaluation: rolling-origin backtest
- At **each origin week**, the data is cut at the origin, the model is refit and h = 1..8 weeks are forecast. Each target week has
  exactly 1 forecast for each h. No information after the origin leaks into the features (lags ≥ 52 are always real values when h ≤ 8).
- **Calibration window**: target weeks 2016-07-04 → 2016-12-26. Used to estimate the forecast intervals.
- **Test window**: target weeks 2017-01-02 → 2017-08-21 (34 weeks × 2 hotels × 8 horizons). MAPE is reported here.
- MAPE = mean of |actual − forecast| / actual, stored as a ratio in `gold.ml_model_metrics` (`dataset = 'backtest'`;
  `'calibration'` for the 2016 window).

| MAPE test 2017 | GBM | Seasonal naive | Moving avg |
|---|---|---|---|
| Overall (h=1..8, 2 hotels) | **8.6%** | 11.6% | 11.8% |
| h=1 City Hotel | 6.7% | 12.2% | **6.6%** |
| h=1 Resort Hotel | **6.2%** | 10.9% | 6.4% |
| h=1..8 City Hotel | **8.4%** | 12.2% | 11.4% |
| h=1..8 Resort Hotel | **8.8%** | 10.9% | 12.2% |
| h=4 | **7.2%** | 11.6% | 10.0% |
| h=8 | 11.8% | **11.6%** | 19.5% |
| Calibration window 2016-H2, overall | **12.0%** | 24.9% | 18.2% |

Observations:
- GBM beats both baselines on overall MAPE (8.6% vs 11.6%/11.8%) and at every horizon from 2 to 7 weeks.
- h=1: GBM ties the moving average (6.5% vs 6.5%): next week is almost equal to the level of the last 4 weeks, which is hard to beat.
- h=8: GBM ties seasonal naive (11.8% vs 11.6%): for far horizons, last year's seasonal information dominates,
  while GBM's recursive errors accumulate.
- Seasonal naive is poor in 2016 (24.9%) because City Hotel in 07–08/2015 is abnormally low (~150–1,000 room-nights/week, vs
  ~1,500 in 2016) — City Hotel data only "ramps up" gradually during 2015.

### Forecast intervals (lower/upper)
Empirical 80% interval: for each h, take the 10% and 90% quantiles of the relative error `actual / forecast − 1`
(both hotels pooled) → `lower = forecast × (1 + q10)`, `upper = forecast × (1 + q90)`.
- 2017 test weeks: quantiles from the 2016 calibration window (no peeking at test). Actual coverage on test:
  GBM 85.7%, seasonal naive 76.5%, moving average 63.6%.
- 8 future weeks: quantiles from all backtest errors (calibration + test), since all of them are known at forecast time.
- The interval is **skewed upward** (upper further than lower) because in 2016 the model often under-forecast when City Hotel
  demand grew strongly vs 2015. Upper may exceed the hotel's real capacity (the dataset has no room counts, rule 10).

### Limitations
- Only ~2 years of data: just 1 year to learn the "same period last year" relationship; the early origins of the calibration window
  (before 07/2016) have no `lag_52` yet, so the model relies only on the recent level and week of year.
- At the summer peak both hotels are almost **fully booked** (Resort ~1,270, City ~1,540 room-nights/week): true demand
  is capped by capacity; the model forecasts room-nights sold, not unconstrained demand.
- Room-nights are counted from **final** non-canceled bookings (known after the stay), so the forecast answers "how many room-nights
  will be sold", not "on-the-books at forecast time" (the dataset has no snapshots by booking date).
- 2 hotels, 1 country: `n_holidays` varies little (≤ 13 holidays/year), so it contributes little.
- The 8 future weeks (2017-08-28 → 2017-10-16) cannot be verified because the dataset ends on 2017-08-31.
