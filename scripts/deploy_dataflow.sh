#!/bin/bash
set -e

PROJECT_ID=${PROJECT_ID:-$(gcloud config get-value project)}
REGION=${REGION:-asia-east2}
BUCKET_NAME="${PROJECT_ID}-mtr-data-lake"
SUBSCRIPTION_NAME=${SUBSCRIPTION_NAME:-mtr-arrivals-dataflow}
JOB_NAME=${JOB_NAME:-mtr-arrivals-streaming-$(date +%Y%m%d%H%M)}

echo "Deploying Dataflow streaming job..."
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Job Name: $JOB_NAME"

cd consumer

python src/main.py \
    --project=$PROJECT_ID \
    --region=$REGION \
    --temp_location=gs://${BUCKET_NAME}/temp \
    --staging_location=gs://${BUCKET_NAME}/staging \
    --runner=DataflowRunner \
    --streaming \
    --job_name=$JOB_NAME \
    --experiments=use_runner_v2 \
    --machine_type=n1-standard-2 \
    --num_workers=1 \
    --max_num_workers=3 \
    --autoscaling_algorithm=THROUGHPUT_BASED

echo "Dataflow job deployed successfully!"
echo "Monitor at: https://console.cloud.google.com/dataflow/jobs?project=$PROJECT_ID"
