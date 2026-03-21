# MTR Real-Time Transit Analytics

A serverless streaming data pipeline that ingests MTR (Hong Kong Mass Transit Railway) train arrival data, processes it, stores it in BigQuery, and visualizes insights via Looker Studio.

## About Hong Kong's MTR System

The **Mass Transit Railway (MTR)** is Hong Kong's major public transport network and one of the most efficient, profitable, and reliable metro systems in the world. Since its inception in 1979, the MTR has grown to become the backbone of Hong Kong's transportation infrastructure.

### Key Statistics

| Metric | Value |
|--------|-------|
| **Daily Ridership** | ~5.8 million passengers |
| **Annual Ridership** | ~1.7 billion passengers |
| **Network Length** | 271 km (168 miles) |
| **Number of Stations** | 99 heavy rail stations |
| **Lines Operated** | 10 lines + Airport Express |
| **On-time Performance** | 99.9% |
| **Fare Recovery Ratio** | ~185% (world's most profitable transit system) |

### Network Coverage

The MTR network connects all major districts across Hong Kong:

| Line | Code | Route | Key Stations |
|------|------|-------|--------------|
| **Tsuen Wan Line** | TWL | Central ↔ Tsuen Wan | Central, Mong Kok, Tsuen Wan |
| **Island Line** | ISL | Kennedy Town ↔ Chai Wan | Central, Causeway Bay, Chai Wan |
| **Kwun Tong Line** | KTL | Whampoa ↔ Tiu Keng Leng | Mong Kok, Kowloon Tong, Kwun Tong |
| **Tseung Kwan O Line** | TKL | North Point ↔ Po Lam/LOHAS Park | Quarry Bay, Tseung Kwan O |
| **Tung Chung Line** | TCL | Hong Kong ↔ Tung Chung | Central, Kowloon, Tung Chung |
| **Airport Express** | AEL | Hong Kong ↔ Airport | Kowloon, Tsing Yi, Airport |
| **Tuen Ma Line** | TML | Tuen Mun ↔ Wu Kai Sha | Yuen Long, Mong Kok, Sha Tin |
| **East Rail Line** | EAL | Admiralty ↔ Lo Wu/Lok Ma Chau | Central, Sha Tin, Border Crossings |
| **South Island Line** | SIL | Admiralty ↔ South Horizons | Ocean Park, Wong Chuk Hang |
| **Disneyland Resort Line** | DRL | Sunny Bay ↔ Disneyland | Disneyland Resort |

### Why MTR Data Matters

The MTR handles nearly **90% of all public transport trips** in Hong Kong, making real-time operational data critical for:

- **Urban Planning**: Understanding passenger flow patterns helps optimize city development
- **Service Reliability**: Monitoring delays enables proactive service improvements
- **Commuter Experience**: Real-time arrival information helps millions plan their journeys
- **Academic Research**: Transit data supports studies on mobility, urbanization, and sustainability

## Problem Statement

Despite the MTR's world-class efficiency, commuters and analysts face several challenges:

- **Uncertainty about train arrival times**: While station displays show arrivals, historical patterns are not easily accessible
- **Unexpected delays during peak hours**: Congestion at interchange stations can cause cascading delays
- **Lack of visibility into service reliability patterns**: No public dashboard shows delay trends by line, time, or station
- **Limited historical analysis**: Real-time data is ephemeral; capturing it enables trend analysis

This project addresses these challenges by building an end-to-end streaming data pipeline that:

1. **Ingests real-time train arrival data** from the MTR Next Train API
2. **Streams data directly** to BigQuery via the streaming API
3. **Stores data** in a partitioned BigQuery data warehouse
4. **Transforms data** using dbt for analytics-ready tables
5. **Visualizes insights** through an interactive Looker Studio dashboard

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
| **Dashboard** | Looker Studio | Data visualization |

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
├── dashboard/                         # Dashboard configuration
│   └── README.md                      # Looker Studio setup guide
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

**Live Dashboard**: [MTR Real-Time Analytics](https://lookerstudio.google.com/reporting/580aa7b2-68b8-44b9-8d7d-a82f41bd6b33)

### Dashboard Tiles

#### Tile 1: Average Wait Time by Line (Categorical)
- **Type**: Bar Chart
- **Dimension**: Line Name
- **Metric**: Average Time Remaining (seconds)
- **Purpose**: Compare service levels across lines

#### Tile 2: Delay Trends Over Time (Temporal)
- **Type**: Time Series Line Chart
- **Dimension**: Hour of Day
- **Metric**: Count of Delayed Trains, Average Delay Duration
- **Purpose**: Identify peak delay periods

## Evaluation Criteria Coverage

| Criteria | Implementation |
|----------|----------------|
| Problem Description | This README + detailed documentation |
| Cloud + IaC | GCP + Terraform |
| Streaming Ingestion | BigQuery Streaming API |
| Data Warehouse | BigQuery with partitioning & clustering |
| Transformations | dbt with staging/marts layers |
| Dashboard | Looker Studio with 2+ tiles |
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
