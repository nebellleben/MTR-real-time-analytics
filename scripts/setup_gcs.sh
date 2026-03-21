#!/bin/bash
set -e

PROJECT_ID=${PROJECT_ID:-$(gcloud config get-value project)}
REGION=${REGION:-asia-east2}
BUCKET_NAME="${PROJECT_ID}-mtr-data-lake"

echo "Creating GCS bucket: $BUCKET_NAME"
gsutil mb -l $REGION gs://${BUCKET_NAME} || echo "Bucket already exists"

echo "Creating temp and staging directories..."
gsutil cp /dev/null gs://${BUCKET_NAME}/temp/.placeholder
gsutil cp /dev/null gs://${BUCKET_NAME}/staging/.placeholder
gsutil cp /dev/null gs://${BUCKET_NAME}/raw/.placeholder
gsutil cp /dev/null gs://${BUCKET_NAME}/curated/.placeholder

echo "GCS bucket setup complete!"
