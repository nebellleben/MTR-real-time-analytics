# MTR Real-Time Transit Analytics

A serverless streaming data pipeline that ingests MTR (Hong Kong Mass Transit Railway) train arrival data, processes it, stores it in BigQuery, and visualizes insights via Streamlit Cloud.

 
This project builds an end-to-end streaming data pipeline that:
 
1. **Ingests real-time train arrival data** from the MTR Next Train API
2. **Streams data directly** to BigQuery via the streaming API
3. **Stores data** in a partitioned BigQuery data warehouse
4. **Transforms data** using dbt for analytics-ready tables
5. **Visualizes insights** through an interactive Streamlit Cloud dashboard

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     SERVERLESS INFRASTRUCTURE (Terraform)                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐     ┌──────────────────────────────────────────────────┐  │
│  │   MTR API   │────▶│              BigQuery Streaming API              │  │
│  │   Producer  │     │   Direct inserts to raw_arrivals table           │  │
│  │   (Python)  │     │   ~$0.01 per 200MB streamed                      │  │
│  └─────────────┘     └──────────────────────────────────────────────────┘  │
│                                              │                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        BigQuery (DWH)                                │   │
│  │   ├─ raw_arrivals (partitioned by date, clustered by line/station)  │   │
│  │   ├─ stg_arrivals (dbt view)                                        │   │
│  │   ├─ dim_lines (dbt table)                                          │   │
│  │   ├─ dim_stations (dbt table)                                       │   │
│  │   └─ fact_delays (dbt table)                                        │   │
│  │                        ~$5/month                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                         │                   │
│                                                         ▼                   │
│                                              ┌─────────────────────────┐   │
│                                              │   Looker Studio         │   │
│                                              │   Dashboard (Free)      │   │
│                                              └─────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘

Total Estimated Cost: ~$5-10/month
```

## Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Cloud Provider** | Google Cloud Platform (GCP) | Infrastructure hosting |
| **Infrastructure as Code** | Terraform | Reproducible infrastructure |
| **Compute** | Local/Cloud Run | Producer script hosting |
| **Streaming** | BigQuery Streaming API | Real-time data ingestion |
| **Data Lake** | Cloud Storage | Raw data storage |
| **Data Warehouse** | BigQuery | Analytical queries |
| **Transformation** | dbt | SQL-based transformations |
| **Dashboard** | Streamlit Cloud | Data visualization |

## Data Source

The pipeline consumes data from the [MTR Open Data API](https://opendata.mtr.com.hk):

- **API**: Next Train API v1.7
- **Update Frequency**: Real-time (every 30 seconds)
- **Coverage**: All MTR lines including:
  - Tung Chung Line (TCL)
  - East Rail Line (EAL)
  - Tseung Kwan O Line (TKL)
  - Kwun Tong Line (KTL)
  - Tsuen Wan Line (TWL)
  - Island Line (ISL)
  - South Island Line (SIL)
  - Tuen Ma Line (TML)
  - Disneyland Resort Line (DRL)
  - Airport Express (AEL)

### Data Fields

| Field | Type | Description |
|-------|------|-------------|
| `arrival_id` | STRING | Unique identifier |
| `line_code` | STRING | MTR line identifier (e.g., "TCL", "EAL") |
| `line_name` | STRING | Full line name |
| `station_code` | STRING | Station identifier |
| `dest_station` | STRING | Destination station |
| `arrival_time` | TIMESTAMP | Expected arrival time |
| `time_remaining` | INT64 | Seconds until arrival |
| `platform` | STRING | Platform number |
| `sequence` | INT64 | Train sequence in the schedule |
| `is_delayed` | BOOLEAN | Whether the train is delayed |
| `delay_seconds` | INT64 | Delay duration in seconds |
| `direction` | STRING | Train direction (DT=Down, UT=Up) |
| `ingestion_timestamp` | TIMESTAMP | When record was ingested |
| `ingestion_date` | DATE | Date partition key |

## Project Structure

```
MTR-real-time-analytics/
├── README.md                          # Project documentation
├── Makefile                           # Common commands
├── docker-compose.yml                 # Local development environment
├── .env.example                       # Environment variables template
│
├── terraform/                         # Infrastructure as Code
│   ├── main.tf                        # Main Terraform configuration
│   ├── variables.tf                   # Input variables
│   └── outputs.tf                     # Output values
│
├── producer/                          # BigQuery streaming producer
│   ├── Dockerfile
│   ├── requirements.txt
│   └── src/
│       └── main.py                    # BigQuery streaming inserts
│
├── dbt_project/                       # dbt transformations
│   ├── dbt_project.yml
│   ├── profiles.yml
│   ├── models/
│   │   ├── staging/
│   │   │   ├── sources.yml
│   │   │   ├── stg_arrivals.sql
│   │   │   └── schema.yml
│   │   └── marts/
│   │       ├── dim_lines.sql
│   │       ├── dim_stations.sql
│   │       ├── fact_delays.sql
│   │       └── schema.yml
│   └── tests/
│
├── dashboard/                         # Streamlit Cloud dashboard
│   ├── app.py
│   ├── requirements.txt
│   └── .streamlit/
│       └── config.toml
│
└── scripts/                           # Utility scripts
    └── run_local.sh                   # Local development script
```

## Prerequisites

- **GCP Account** with billing enabled
- **GCP CLI** (`gcloud`) installed and authenticated
- **Terraform** >= 1.0
- **Docker** >= 20.0
- **Python** >= 3.9
- **dbt** >= 1.5 (with BigQuery adapter)

## Quick Start

### 1. Clone and Configure

```bash
git clone https://github.com/yourusername/MTR-real-time-analytics.git
cd MTR-real-time-analytics

cp .env.example .env
vim .env  # Edit with your GCP project details
```

### 2. Deploy Infrastructure

```bash
make infra-init
make infra-apply
```

### 3. Run Producer (Stream Data to BigQuery)

```bash
cd producer
pip install -r requirements.txt
export PROJECT_ID=de-zoomcamp-485516
export BIGQUERY_DATASET=mtr_analytics
export BIGQUERY_TABLE=raw_arrivals
python src/main.py
```

### 4. Run dbt Transformations

```bash
cd dbt_project
python3.11 -m venv .venv311
source .venv311/bin/activate
pip install dbt-bigquery
BIGQUERY_PROJECT=de-zoomcamp-485516 dbt run
BIGQUERY_PROJECT=de-zoomcamp-485516 dbt test
```

### 5. Connect Looker Studio

1. Open [Looker Studio](https://lookerstudio.google.com)
2. Create new data source → BigQuery
3. Select project → dataset → `fact_delays`
4. Build dashboard tiles

## Makefile Commands

```bash
make help                    # Show all available commands
make infra-init              # Initialize Terraform
make infra-apply             # Apply Terraform changes
make infra-destroy           # Destroy infrastructure
make dbt-run                 # Run dbt models
make dbt-test                # Run dbt tests
make local-up                # Start local development
make local-down              # Stop local development
```

## BigQuery Schema

### Raw Layer (Partitioned)

```sql
-- raw_arrivals - Partitioned by ingestion_date, Clustered by line_code
CREATE TABLE `{{project}}.{{dataset}}.raw_arrivals`
(
    arrival_id STRING NOT NULL,
    line_code STRING NOT NULL,
    line_name STRING,
    station_code STRING NOT NULL,
    dest_station STRING,
    arrival_time TIMESTAMP,
    time_remaining INT64,
    platform STRING,
    sequence INT64,
    is_delayed BOOLEAN,
    delay_seconds INT64,
    direction STRING,
    ingestion_timestamp TIMESTAMP NOT NULL,
    ingestion_date DATE NOT NULL
)
PARTITION BY ingestion_date
CLUSTER BY line_code, station_code;
```

### Mart Layer (dbt)

| Table | Description |
|-------|-------------|
| `stg_arrivals` | Cleaned and deduplicated arrival data (view) |
| `dim_lines` | MTR line reference data |
| `dim_stations` | Station reference data with line associations |
| `fact_delays` | Aggregated delay metrics by time, line, station |

## Dashboard

**Live Dashboard**: [MTR Wait Time Analysis](https://g7y8eyjubppvkm5mqndgm7.streamlit.app/)

### Dashboard Features

The Streamlit dashboard provides comprehensive wait time analysis:

#### 1. Overview Metrics
- Total arrivals, average/max wait times
- Active lines and stations count
- Real-time data freshness indicator

#### 2. Hourly Trends
- Interactive line chart showing wait time by hour and line
- Heatmap visualization of wait patterns
- Peak hour identification

#### 3. Line Analysis
- Bar chart comparing average wait times across lines
- Box plot showing wait time distribution per line
- Detailed statistics table with std dev, min, max

#### 4. Station Analysis
- Individual station hourly patterns
- Direction comparison (UP/DOWN)
- Top 10 stations with longest wait times

#### 5. Distribution Analysis
- Histogram with box plot marginal
- Cumulative distribution function (CDF)
- Percentile breakdown (10th to 99th)

#### 6. Anomaly Detection
- Automatic detection of unusually long/short waits
- Statistical thresholds (mean ± 2σ)
- Visual anomaly scatter plot by line and hour

### Deploy Your Own Dashboard

1. **Fork the repository**

2. **Create Streamlit Cloud app**:
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Connect your GitHub account
   - Select the forked repository
   - Set main file path: `dashboard/app.py`

3. **Set environment variables** (if needed):
   - In Streamlit Cloud settings, add secrets:
   ```toml
   [gcp_service_account]
   # Only needed if not using gcloud ADC
   ```

4. **Deploy** - Streamlit Cloud will automatically deploy and provide a URL

## Evaluation Criteria Coverage

| Criteria | Implementation |
|----------|----------------|
| Problem Description | This README + detailed documentation |
| Cloud + IaC | GCP + Terraform |
| Streaming Ingestion | BigQuery Streaming API |
| Data Warehouse | BigQuery with partitioning & clustering |
| Transformations | dbt with staging/marts layers |
| Dashboard | Streamlit Cloud with interactive visualizations |
| Reproducibility | Makefile + detailed README |

## Going the Extra Mile

| Feature | Status |
|---------|--------|
| CI/CD Pipeline (GitHub Actions) | Planned |
| Unit Tests (pytest) | Planned |
| Data Quality Tests (dbt) | ✅ Completed (21 tests) |
| Monitoring & Alerting | Planned |
| dbt Documentation | ✅ Completed |

## License

This project is licensed under the MIT License.
