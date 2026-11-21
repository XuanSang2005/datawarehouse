# Business Problem Definition

> This is the source content for **Chapter 2: Business problem definition** of the report and slides.

## 1. Organizational context

A hotel group in Portugal operates two properties:
- **City Hotel**: a city hotel in Lisbon
- **Resort Hotel**: a seaside resort in the Algarve

Booking data from 07/2015 to 08/2017 (119,390 bookings) reveals the following problems:

| Problem | Evidence from the data |
|---|---|
| **Very high cancellation rate** | 37.0% overall; City Hotel 41.7%, Resort Hotel 27.8% |
| **Strong seasonal swings in demand and price** | July–August have the most arrivals; the Resort's ADR is about €174 in August versus about €49 in January (~3.5 times higher) |
| **Dependence on intermediary channels** | 82% of bookings come through the TA/TO channel (travel agents, OTAs); only 12% are direct bookings |
| **Fragmented data with no centralized analytics system** | Decisions rely on experience and Excel reports |

Rooms cancelled close to the arrival date cannot be resold in time, which results in directly lost revenue. Conversely,
excessive overbooking means guests arrive to find no room available, which incurs compensation costs and damages the hotel's reputation.

## 2. Decision makers

| Decision maker | Specific decisions | Frequency |
|---|---|---|
| **Revenue Manager** | Overbooking level by week/segment; deposit requirements for high-risk bookings; seasonal price adjustments | Weekly |
| **Sales & Marketing Manager** | Budget allocation by channel (OTA, direct, corporate) and country market; promotion timing | Monthly/quarterly |
| **General Manager** | Performance evaluation of the two hotels; strategic priorities | Monthly |
| **Reservations department** | Reconfirmation calls for bookings with a high risk of cancellation | Daily |

## 3. Expected objectives

| # | Objective | Measure of success |
|---|---|---|
| G1 | Provide a centralized view of KPIs (revenue, room-nights, ADR, cancellation rate) across multiple dimensions | Dashboard with filtering/drill-down by hotel, time, channel and country |
| G2 | Predict which bookings will be cancelled | AUC ≥ 0.85 on a time-based test set (year 2017) |
| G3 | Forecast weekly demand (room-nights) | MAPE over the backtest period |
| G4 | Support overbooking and deposit decisions | What-if simulation: revenue recovered versus the risk of running out of rooms |
| G5 | Identify the most valuable channels and markets | Ranking by realized revenue (after cancellations), ADR and cancellation rate |

## 4. Scope

**In scope:** historical data of the two hotels; descriptive, diagnostic, predictive and prescriptive analytics; an interactive web application.

**Out of scope:** real-time direct integration with the PMS; automated dynamic price optimization.

**Assumptions and limitations:**
- The dataset **does not include the number of rooms** of each hotel, so occupancy and RevPAR can only be computed when the user enters the capacity as a parameter.
- There is no cost data (OTA commissions, overbooking compensation costs): these are introduced as **adjustable parameters** in the what-if analysis.
- Hotel names are anonymized in the original dataset.

## 5. Proposed solution (summary)

1. A PostgreSQL **lakehouse** following the medallion architecture: integrates booking, public holiday and weather data.
2. A **star schema** in the Gold layer, serving OLAP analysis.
3. **Analytics**: a cancellation prediction model and a demand forecasting model.
4. A **web application** for each decision maker: KPI dashboard, cancellation risk, forecasting, what-if simulation.

Technical details: [`ARCHITECTURE.md`](ARCHITECTURE.md)
