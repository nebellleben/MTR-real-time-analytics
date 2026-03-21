#!/bin/bash
set -e

PROJECT_ID=${PROJECT_ID:-de-zoomcamp-485516}
REGION=${REGION:-asia-east2}
BUCKET_NAME="${PROJECT_ID}-mtr-data-lake"
DATASET_NAME=${DATASET_NAME:-mtr_analytics}

echo "=== Setting up MTR Analytics Infrastructure ==="
echo "Project: $PROJECT_ID"
echo "Region: $REGION"

# 1. Create GCS bucket
echo ""
echo "1. Creating GCS bucket..."
gsutil mb -l $REGION gs://${BUCKET_NAME} 2>/dev/null || echo "   Bucket already exists"
gsutil cp /dev/null gs://${BUCKET_NAME}/temp/.placeholder 2>/dev/null || true
gsutil cp /dev/null gs://${BUCKET_NAME}/staging/.placeholder 2>/dev/null || true
echo "   Created: gs://${BUCKET_NAME}"

# 2. Create Pub/Sub topic and subscription
echo ""
echo "2. Setting up Pub/Sub..."
gcloud pubsub topics create mtr-arrivals --project=$PROJECT_ID 2>/dev/null || echo "   Topic already exists"
gcloud pubsub subscriptions create mtr-arrivals-dataflow \
    --topic=mtr-arrivals \
    --project=$PROJECT_ID \
    --ack-deadline=60 \
    2>/dev/null || echo "   Subscription already exists"
echo "   Created topic: mtr-arrivals"
echo "   Created subscription: mtr-arrivals-dataflow"

# 3. Create BigQuery dataset and table
echo ""
echo "3. Setting up BigQuery..."
bq mk --dataset --location=$REGION ${PROJECT_ID}:${DATASET_NAME} 2>/dev/null || echo "   Dataset already exists"

# Create raw_arrivals table
bq mk --table \
    --time_partitioning_field=ingestion_date \
    --time_partitioning_type=DAY \
    --clustering_fields=line_code,station_code \
    ${PROJECT_ID}:${DATASET_NAME}.raw_arrivals \
    arrival_id:STRING,line_code:STRING,line_name:STRING,station_code:STRING,station_name:STRING,dest_station:STRING,arrival_time:TIMESTAMP,time_remaining:INT64,platform:STRING,sequence:INT64,is_delayed:BOOLEAN,delay_seconds:INT64,ingestion_timestamp:TIMESTAMP,ingestion_date:DATE \
    2>/dev/null || echo "   Table already exists"
echo "   Created dataset: ${DATASET_NAME}"
echo "   Created table: raw_arrivals"

echo ""
echo "=== Infrastructure setup complete! ==="
