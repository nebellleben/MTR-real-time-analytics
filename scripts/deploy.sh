#!/bin/bash
set -e

set -x

PROJECT_ID=${PROJECT_ID:-de-zoomcamp-485516}
REGION=${REGION:-asia-east2}
BUCKET_NAME="${PROJECT_ID}-mtr-data-lake"
DATASET_NAME=${DATASET_NAME:-mtr_analytics}
SUBSCRIPTION_NAME=mtr-arrivals-dataflow

JOB_NAME="mtr-dataflow-$(date +%Y%m%d%H%M)"

echo "Deploying Dataflow streaming job..."
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Bucket: $BUCKET_NAME"
echo "Dataset: $DATASET_NAME"
echo "Subscription: $SUBSCRIPTION_NAME"
echo "Job name: $JOB_NAME"

cd ~/dev/MTR-real-time-analytics
pip install -q apache-beam[gcp]==2.50.0
pip install google-cloud-pubsub
pip install google-cloud-bigquery

cd consumer
python src/main.py \
    --runner=DataflowRunner \
    --streaming \
    --temp_location=gs://${BUCKET_NAME}/temp \
    --staging_location=gs://${BUCKET_NAME}/staging \
    --project=$PROJECT_ID \
    --region=$REGION \
    --subscription=projects/$PROJECT_ID/subscriptions/$SUBSCRIPTION_NAME \
    --experiments=use_runner_v2 \
    --machine_type=n1-standard-2 \
    --max_num_workers=1 \
    --num_workers=1 \
    --save_main_session=true
    --job_name=$JOB_NAME \
    2>&1 | tail -20
echo "Dataflow job submitted: $JOB_NAME"
echo "Waiting for job to start..."
sleep 30
gcloud dataflow jobs list --project=$PROJECT_ID --region=$REGION | head -5
echo ""
echo "3. Checking BigQuery tables..."
bq ls --project_id=$PROJECT_ID --dataset_id=$DATASET_NAME 2>&1 | head -5
echo ""
echo "4. Waiting for Dataflow job to start..."
sleep 30
gcloud dataflow jobs describe --project=$PROJECT_ID --region=$REGION --job=$JOB_NAME 2>&1 | grep "state" || echo "No status yet"
echo ""
echo "5. Checking subscription..."
gcloud pubsub subscriptions describe mtr-arrivals-dataflow --project=$PROJECT_ID --region=$REGION
