#!/bin/bash
set -e

PROJECT_ID=${PROJECT_ID:-$(gcloud config get-value project)}
REGION=${REGION:-asia-east2}
TOPIC_NAME=${TOPIC_NAME:-mtr-arrivals}
SUBSCRIPTION_NAME=${SUBSCRIPTION_NAME:-mtr-arrivals-dataflow}

echo "Setting up Pub/Sub resources..."
echo "Project: $PROJECT_ID"
echo "Region: $REGION"

echo "Creating Pub/Sub topic: $TOPIC_NAME"
gcloud pubsub topics create $TOPIC_NAME --project=$PROJECT_ID || echo "Topic already exists"

echo "Creating Pub/Sub subscription: $SUBSCRIPTION_NAME"
gcloud pubsub subscriptions create $SUBSCRIPTION_NAME \
    --topic=$TOPIC_NAME \
    --project=$PROJECT_ID \
    --ack-deadline=60 \
    --message-retention-period=604800s || echo "Subscription already exists"

echo "Pub/Sub setup complete!"
