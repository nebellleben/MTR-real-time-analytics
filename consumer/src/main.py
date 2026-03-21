"""
Dataflow Streaming Job - consumes MTR arrival data from Pub/Sub and writes to BigQuery.
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, List

import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions, StandardOptions
from apache_beam.io.gcp.pubsub import ReadFromPubSub
from apache_beam.io.gcp.bigquery import WriteToBigQuery, BigQueryDisposition

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ParseArrivalFn(beam.DoFn):
    def process(self, element: bytes):
        try:
            data = json.loads(element.decode("utf-8"))
            yield data
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse message: {e}")


class EnrichArrivalFn(beam.DoFn):
    def __init__(self, delay_threshold: int = 300):
        self.delay_threshold = delay_threshold

    def process(self, element: Dict[str, Any]):
        try:
            arrival_time_str = element.get("arrival_time", "")
            ingestion_time_str = element.get("ingestion_timestamp", "")

            if arrival_time_str:
                arrival_time = datetime.fromisoformat(
                    arrival_time_str.replace("Z", "+00:00")
                )
            else:
                arrival_time = datetime.utcnow()

            if ingestion_time_str:
                ingestion_time = datetime.fromisoformat(
                    ingestion_time_str.replace("Z", "+00:00")
                )
            else:
                ingestion_time = datetime.utcnow()

            time_remaining = element.get("time_remaining", 0)
            is_delayed = time_remaining > self.delay_threshold
            delay_seconds = (
                max(0, time_remaining - self.delay_threshold) if is_delayed else 0
            )

            enriched = {
                "arrival_id": element.get("arrival_id", ""),
                "line_code": element.get("line_code", ""),
                "line_name": element.get("line_name", ""),
                "station_code": element.get("station_code", ""),
                "station_name": element.get("station_name", ""),
                "dest_station": element.get("dest_station", ""),
                "platform": element.get("platform", ""),
                "sequence": element.get("sequence", 0),
                "arrival_time": arrival_time.isoformat(),
                "time_remaining": time_remaining,
                "is_delayed": is_delayed,
                "delay_seconds": delay_seconds,
                "ingestion_timestamp": ingestion_time.isoformat(),
                "ingestion_date": ingestion_time.strftime("%Y-%m-%d"),
            }
            yield enriched
        except Exception as e:
            logger.error(f"Failed to enrich arrival: {e}")


def get_table_schema() -> str:
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
    project_id = os.getenv("PROJECT_ID", "de-zoomcamp-485516")
    subscription = os.getenv("PUBSUB_SUBSCRIPTION", "mtr-arrivals-dataflow")
    table = os.getenv("BIGQUERY_TABLE", "mtr_analytics.raw_arrivals")
    temp_location = os.getenv(
        "TEMP_LOCATION", "gs://de-zoomcamp-485516-mtr-data-lake/temp"
    )
    staging_location = os.getenv(
        "STAGING_LOCATION", "gs://de-zoomcamp-485516-mtr-data-lake/staging"
    )
    region = os.getenv("REGION", "asia-east2")

    pipeline_options = PipelineOptions(
        argv,
        project=project_id,
        runner="DataflowRunner",
        streaming=True,
        temp_location=temp_location,
        staging_location=staging_location,
        region=region,
        save_main_session=True,
    )

    standard_options = pipeline_options.view_as(StandardOptions)
    standard_options.streaming = True

    subscription_path = f"projects/{project_id}/subscriptions/{subscription}"

    logger.info(f"Starting Dataflow pipeline")
    logger.info(f"Subscription: {subscription_path}")
    logger.info(f"Table: {table}")

    with beam.Pipeline(options=pipeline_options) as p:
        (
            p
            | "Read from Pub/Sub" >> ReadFromPubSub(subscription=subscription_path)
            | "Parse JSON" >> beam.ParDo(ParseArrivalFn())
            | "Enrich Arrival" >> beam.ParDo(EnrichArrivalFn())
            | "Filter Valid"
            >> beam.Filter(lambda x: x is not None and "arrival_id" in x)
            | "Write to BigQuery"
            >> WriteToBigQuery(
                table=table,
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
