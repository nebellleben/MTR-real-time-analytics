# MTR Real-Time Transit Analytics

A serverless streaming data pipeline that ingests MTR (Hong Kong Mass Transit Railway) train arrival data, processes it, stores it in BigQuery, and visualizes insights via Streamlit Cloud.

## Overview

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
│                                              │   Streamlit Cloud       │   │
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

### Wait Time Calculation

The wait time represents the expected wait time for a random passenger arriving at the platform at a uniform time. It is calculated using **only the first arriving train's wait time** from the API, simulating the passenger experience.

### Data Fields

| Field | Type | Description |
|-------|------|-------------|
| `arrival_id` | STRING | Unique identifier |
| `line_code` | STRING | MTR line identifier (e.g., "TCL", "EAL") |
| `line_name` | STRING | Full line name |
| `station_code` | STRING | Station identifier |
| `dest_station` | STRING | Destination station |
| `arrival_time` | TIMESTAMP | Expected arrival time |
| `time_remaining` | INT64 | Seconds until first train arrives |
| `platform` | STRING | Platform number |
| `sequence` | INT64 | Train sequence (always 1 for first train) |
| `direction` | STRING | Train direction (UP/DOWN) |
| `ingestion_timestamp` | TIMESTAMP | When record was ingested |
| `ingestion_date` | DATE | Date partition key |

## Project Structure

```
MTR-real-time-analytics/
├── README.md                          # Project documentation
├── Makefile                           # Common commands
├── .env.example                       # Environment variables template
│
├── terraform/                         # Infrastructure as Code
│   ├── main.tf                        # Main Terraform configuration
│   └── variables.tf                   # Input variables
│
├── producer/                          # BigQuery streaming producer
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
└── credentials/                       # Service account keys (gitignored)
```

## Prerequisites

- **GCP Account** with billing enabled
- **GCP CLI** (`gcloud`) installed and authenticated
- **Terraform** >= 1.0
- **Python** >= 3.11
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
python3.11 -m venv .venv311
source .venv311/bin/activate
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

### 5. Access Dashboard

The live dashboard is available at: [MTR Wait Time Analysis](https://g7y8eyjubppvkm5mqndgm7.streamlit.app/)

## Makefile Commands

```bash
make help                    # Show all available commands
make infra-init              # Initialize Terraform
make infra-apply             # Apply Terraform changes
make infra-destroy           # Destroy infrastructure
make dbt-run                 # Run dbt models
make dbt-test                # Run dbt tests
make streamlit-run           # Run Streamlit dashboard locally
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
| `fact_delays` | Aggregated wait time metrics by time, line, station |

## Dashboard

**Live Dashboard**: [MTR Wait Time Analysis](https://g7y8eyjubppvkm5mqndgm7.streamlit.app/)

### Dashboard Features

The Streamlit dashboard provides comprehensive wait time analysis with official MTR line colors:

#### 1. Overview Metrics
- Total arrivals count
- **Average wait time** (in minutes)
- **Standard deviation** of wait times
- **Outlier count** (wait times beyond ±2 standard deviations)
- Active lines count

#### 2. Hourly Trends
- Interactive line chart showing wait time by hour and line
- Heatmap visualization of wait patterns
- Peak hour identification

#### 3. Line Analysis
- Bar chart comparing average wait times across lines
- Box plot showing wait time distribution per line
- **Detailed statistics table** with:
  - Average wait time
  - Standard deviation
  - Variance
  - Min/Max values
  - **Outlier count per line (±2 SD)**

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

### MTR Line Colors

The dashboard uses official MTR line colors for consistency:

| Line | Color |
|------|-------|
| Tsuen Wan Line | Red (#ED1D24) |
| Kwun Tong Line | Green (#00A040) |
| Island Line | Blue (#0075C2) |
| Tseung Kwan O Line | Purple (#7D4990) |
| Tung Chung Line | Orange (#F7943E) |
| Airport Express | Teal (#00888C) |
| Disneyland Resort Line | Pink (#D4849A) |
| East Rail Line | Cyan (#5FC0D3) |
| Tuen Ma Line | Brown (#9A3B26) |
| South Island Line | Lime (#B5D334) |

### Deploy Your Own Dashboard

1. **Fork the repository**

2. **Create Streamlit Cloud app**:
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Connect your GitHub account
   - Select the forked repository
   - Set main file path: `dashboard/app.py`

3. **Configure BigQuery Authentication**:
   - Create a GCP service account with BigQuery access:
     ```bash
     gcloud iam service-accounts create streamlit-dashboard \
       --display-name="Streamlit Dashboard" \
       --project=YOUR_PROJECT_ID
     
     gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
       --member="serviceAccount:streamlit-dashboard@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
       --role="roles/bigquery.dataViewer"
     
     gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
       --member="serviceAccount:streamlit-dashboard@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
       --role="roles/bigquery.jobUser"
     
     gcloud iam service-accounts keys create credentials/streamlit-service-account.json \
       --iam-account=streamlit-dashboard@YOUR_PROJECT_ID.iam.gserviceaccount.com
     ```
   
   - In Streamlit Cloud settings, add secrets:
     ```toml
     [gcp_service_account]
     type = "service_account"
     project_id = "YOUR_PROJECT_ID"
     private_key_id = "..."
     private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
     client_email = "streamlit-dashboard@YOUR_PROJECT_ID.iam.gserviceaccount.com"
     client_id = "..."
     auth_uri = "https://accounts.google.com/o/oauth2/auth"
     token_uri = "https://oauth2.googleapis.com/token"
     auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
     client_x509_cert_url = "..."
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
| Data Quality Tests (dbt) | Completed |
| Monitoring & Alerting | Planned |
| dbt Documentation | Completed |
| Statistical Analysis (variance, outliers) | Completed |
| Official MTR Line Colors | Completed |

## License

This project is licensed under the MIT License.
