"""
Dataflow Streaming Job - consumes MTR arrival data from Pub/Sub and writes to BigQuery.
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any

import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions, StandardOptions
from apache_beam.io.gcp.pubsub import ReadFromPubSub
from apache_beam.io.gcp.bigquery import WriteToBigQuery, BigQueryDisposition
from google.cloud import bigquery

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PipelineConfig:
    PROJECT_ID = os.getenv("PROJECT_ID", "your-project-id")
    PUBSUB_SUBSCRIPTION = os.getenv("PUBSUB_SUBSCRIPTION", "mtr-arrivals-dataflow")
    BIGQUERY_TABLE = os.getenv("BIGQUERY_TABLE", "mtr_analytics.raw_arrivals")
    TEMP_LOCATION = os.getenv("TEMP_LOCATION", "gs://mtr-analytics-temp/temp")
    STAGING_LOCATION = os.getenv("STAGING_LOCATION", "gs://mtr-analytics-temp/staging")


class ParseArrivalFn(beam.DoFn):
    """Parse JSON message from Pub/Sub"""

    def process(self, element: bytes):
        try:
            data = json.loads(element.decode("utf-8"))
            yield data
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse message: {e}")
            return


class EnrichArrivalFn(beam.DoFn):
    """Enrich arrival data with computed fields"""

    def process(self, element: Dict[str, Any]):
        try:
            arrival_time = datetime.fromisoformat(element.get("arrival_time", ""))
            ingestion_time = datetime.fromisoformat(
                element.get("ingestion_timestamp", "")
            )

            time_remaining = element.get("time_remaining", 0)
            delay_threshold = 300

            is_delayed = time_remaining > delay_threshold
            delay_seconds = (
                max(0, time_remaining - delay_threshold) if is_delayed else 0
            )

            enriched = {
                **element,
                "is_delayed": is_delayed,
                "delay_seconds": delay_seconds,
                "arrival_time": arrival_time.isoformat(),
                "ingestion_timestamp": ingestion_time.isoformat(),
            }

            yield enriched
        except Exception as e:
            logger.error(f"Failed to enrich arrival: {e}")
            return


def get_table_schema():
    """Return BigQuery table schema"""
    return ",".join(
        [
            "arrival_id:STRING",
            "line_code:STRING",
            "line_name:STRING",
            "station_code:STRING",
            "station_name:STRING",
            "dest_station:STRING",
            "platform:STRING",
            "sequence:INTEGER",
            "arrival_time:TIMESTAMP",
            "time_remaining:INTEGER",
            "is_delayed:BOOLEAN",
            "delay_seconds:INTEGER",
            "ingestion_timestamp:TIMESTAMP",
            "ingestion_date:DATE",
        ]
    )


def run_pipeline(argv=None):
    """Main pipeline entry point"""
    config = PipelineConfig()

    pipeline_options = PipelineOptions(
        argv,
        project=config.PROJECT_ID,
        runner="DataflowRunner",
        streaming=True,
        temp_location=config.TEMP_LOCATION,
        staging_location=config.STAGING_LOCATION,
        region=os.getenv("REGION", "asia-east2"),
        save_main_session=True,
    )

    standard_options = pipeline_options.view_as(StandardOptions)
    standard_options.streaming = True

    subscription_path = (
        f"projects/{config.PROJECT_ID}/subscriptions/{config.PUBSUB_SUBSCRIPTION}"
    )

    logger.info(f"Starting Dataflow pipeline reading from {subscription_path}")
    logger.info(f"Writing to BigQuery table {config.BIGQUERY_TABLE}")

    with beam.Pipeline(options=pipeline_options) as pipeline:
        (
            pipeline
            | "Read from Pub/Sub" >> ReadFromPubSub(subscription=subscription_path)
            | "Parse JSON" >> beam.ParDo(ParseArrivalFn())
            | "Enrich Arrival" >> beam.ParDo(EnrichArrivalFn())
            | "Filter Valid"
            >> beam.Filter(lambda x: x is not None and "arrival_id" in x)
            | "Write to BigQuery"
            >> WriteToBigQuery(
                table=config.BIGQUERY_TABLE,
                schema=get_table_schema(),
                create_disposition=BigQueryDisposition.CREATE_IF_NEEDED,
                write_disposition=BigQueryDisposition.WRITE_APPEND,
                additional_bq_parameters={
                    "timePartitioning": {"field": "ingestion_date"},
                    "clustering": {"fields": ["line_code", "station_code"]},
                },
            )
        )

    logger.info("Pipeline completed")


if __name__ == "__main__":
    run_pipeline()
