#!/bin/bash
set -e

NAMESPACE=${NAMESPACE:-mtr-analytics}
KAFKA_TOPIC=${KAFKA_TOPIC:-mtr-arrivals}
PARTITIONS=${PARTITIONS:-6}
REPLICATION_FACTOR=${REPLICATION_FACTOR:-3}

echo "Creating Kafka topic: $KAFKA_TOPIC"
kubectl exec -n mtr-analytics -c kafka-0 -- kafka-topics.sh --create \
  --topic $KAFKA_TOPIC \
  --partitions $PARTITIONS \
  --replication-factor $REPLICATION_FACTOR \
  --if-not-exists || true

echo "Topic $KAFKA_TOPIC created or ready!"
