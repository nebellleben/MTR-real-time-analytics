#!/bin/bash
set -e

PROJECT_ID=${PROJECT_ID:-$(gcloud config get-value project)}
REGION=${REGION:-asia-east2}
BUCKET_NAME="${PROJECT_ID}-mtr-data-lake"
DATASET_NAME=${DATASET_NAME:-mtr_analytics}

echo "Creating BigQuery dataset: $DATASET_NAME"
bq mk --dataset --location=$REGION ${PROJECT_ID}:${DATASET_NAME} || echo "Dataset already exists"

echo "Creating raw_arrivals table..."
bq mk --table \
    --time_partitioning_field=ingestion_date \
    --time_partitioning_type=DAY \
    --clustering_fields=line_code,station_code \
    ${PROJECT_ID}:${DATASET_NAME}.raw_arrivals \
    arrival_id:STRING,line_code:STRING,station_code:STRING,station_name:STRING,dest_station:STRING,arrival_time:TIMESTAMP,time_remaining:INT64,platform:STRING,sequence:INT64,is_delayed:BOOLEAN,delay_seconds:INT64,ingestion_timestamp:TIMESTAMP,ingestion_date:DATE \
    || echo "Table already exists"

echo "BigQuery setup complete!"
