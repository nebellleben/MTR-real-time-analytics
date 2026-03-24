"""
MTR API Producer - fetches real-time MTR arrival data and streams to BigQuery.
"""

import os
import json
import time
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, List

from google.cloud import bigquery
from google.api_core import retry
import requests
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Config:
    PROJECT_ID = os.getenv("PROJECT_ID", "de-zoomcamp-485516")
    BIGQUERY_DATASET = os.getenv("BIGQUERY_DATASET", "mtr_analytics")
    BIGQUERY_TABLE = os.getenv("BIGQUERY_TABLE", "raw_arrivals")
    MTR_API_BASE_URL = os.getenv(
        "MTR_API_BASE_URL", "https://rt.data.gov.hk/v1/transport/mtr"
    )
    POLL_INTERVAL = int(os.getenv("POLL_INTERVAL_SECONDS", "30"))
    MTR_LINES = os.getenv("MTR_LINES", "TCL,EAL,TML,TKL,KTL,TWL,ISL,SIL,DRL,AEL").split(
        ","
    )


class MTRClient:
    """Client for MTR Open Data API"""

    MTR_LINE_NAMES = {
        "TCL": "Tung Chung Line",
        "EAL": "East Rail Line",
        "TML": "Tuen Ma Line",
        "TKL": "Tseung Kwan O Line",
        "KTL": "Kwun Tong Line",
        "TWL": "Tsuen Wan Line",
        "ISL": "Island Line",
        "SIL": "South Island Line",
        "DRL": "Disneyland Resort Line",
        "AEL": "Airport Express",
    }

    MTR_STATIONS = {
        "TWL": [
            "CEN",
            "ADM",
            "TST",
            "TSW",
            "JOR",
            "YMT",
            "MOK",
            "PRE",
            "LAK",
            "CSW",
            "HOM",
            "SKM",
            "KLB",
            "SSP",
            "PRC",
            "TWH",
            "TWK",
            "TSF",
        ],
        "ISL": ["KET", "HFC", "CAB", "TIH", "EXC", "QUB", "SYH", "WAC", "CEN", "ADM"],
        "KTL": [
            "WHA",
            "NAC",
            "QUB",
            "YAT",
            "KOW",
            "LAT",
            "CHH",
            "MOK",
            "KOT",
            "SKM",
            "HOM",
            "YMT",
            "NGK",
            "KOB",
        ],
        "TKL": ["NOP", "QUB", "YAT", "TIK", "TKO", "HAH", "POA", "LHP"],
        "TCL": ["HOK", "KOW", "OLY", "NAC", "LAC", "TSY", "SUN", "TUC"],
        "EAL": [
            "ADM",
            "EXC",
            "HUH",
            "MKK",
            "KOT",
            "TAW",
            "SHT",
            "FOT",
            "UNI",
            "TAP",
            "RAC",
            "LOW",
            "LMC",
        ],
        "TML": [
            "TUK",
            "TIW",
            "KSU",
            "AUS",
            "MOS",
            "HEO",
            "TSH",
            "SIH",
            "CIO",
            "TWW",
            "AWE",
            "KSR",
            "TIS",
            "TSH",
            "HHS",
            "HUH",
            "ETS",
            "AUS",
            "OLY",
            "NAC",
            "MEF",
            "HOK",
            "EXC",
        ],
        "AEL": ["HOK", "KOW", "TSY", "AIR", "AWE"],
        "SIL": ["ADM", "OCP", "QUB", "SOH", "LET", "WCH"],
        "DRL": ["SUN", "DIS"],
    }

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/json",
            }
        )

    def get_schedule(self, line_code: str, station_code: str) -> Dict[str, Any]:
        try:
            url = f"{self.base_url}/getSchedule.php?line={line_code}&sta={station_code}"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data
        except requests.exceptions.RequestException as e:
            logger.error(
                f"Failed to fetch schedule for {line_code}-{station_code}: {e}"
            )
            return {}

    def parse_arrivals(
        self, line_code: str, station_code: str, schedule_data: Dict
    ) -> List[Dict[str, Any]]:
        arrivals = []
        now = datetime.utcnow()

        data_key = f"{line_code}-{station_code}"
        station_data = schedule_data.get("data", {}).get(data_key, {})

        if not station_data:
            return arrivals

        for direction in ["UP", "DOWN"]:
            schedules = station_data.get(direction, [])
            if not schedules:
                continue

            sorted_schedules = sorted(schedules, key=lambda x: int(x.get("seq", 0)))

            first_train = sorted_schedules[0] if sorted_schedules else None
            if not first_train:
                continue

            try:
                time_remaining = int(first_train.get("ttnt", 0)) * 60
                if time_remaining < 0:
                    continue

                arrival_time_str = first_train.get("time", "")
                if arrival_time_str:
                    arrival_time = datetime.strptime(
                        arrival_time_str, "%Y-%m-%d %H:%M:%S"
                    )
                else:
                    arrival_time = now

                arrival = {
                    "arrival_id": str(uuid.uuid4()),
                    "line_code": line_code,
                    "line_name": self.MTR_LINE_NAMES.get(line_code, "Unknown"),
                    "station_code": station_code,
                    "dest_station": first_train.get("dest", ""),
                    "platform": first_train.get("plat", ""),
                    "sequence": 1,
                    "arrival_time": arrival_time.isoformat(),
                    "time_remaining": time_remaining,
                    "direction": direction,
                    "ingestion_timestamp": now.isoformat(),
                    "ingestion_date": now.strftime("%Y-%m-%d"),
                }
                arrivals.append(arrival)
            except (ValueError, KeyError) as e:
                logger.warning(f"Failed to parse schedule entry: {e}")
                continue

        return arrivals

        for direction in ["UP", "DOWN"]:
            schedules = station_data.get(direction, [])
            if not schedules:
                continue

            sorted_schedules = sorted(schedules, key=lambda x: int(x.get("seq", 0)))

            first_train = sorted_schedules[0]

            try:
                time_remaining = int(first_train.get("ttnt", 0)) * 60
                if time_remaining < 0:
                    continue

                arrival_time_str = first_train.get("time", "")
                if arrival_time_str:
                    arrival_time = datetime.strptime(
                        arrival_time_str, "%Y-%m-%d %H:%M:%S"
                    )
                else:
                    arrival_time = now

                arrival = {
                    "arrival_id": str(uuid.uuid4()),
                    "line_code": line_code,
                    "line_name": self.MTR_LINE_NAMES.get(line_code, "Unknown"),
                    "station_code": station_code,
                    "dest_station": first_train.get("dest", ""),
                    "platform": first_train.get("plat", ""),
                    "sequence": 1,
                    "arrival_time": arrival_time.isoformat(),
                    "time_remaining": time_remaining,
                    "direction": direction,
                    "ingestion_timestamp": now.isoformat(),
                    "ingestion_date": now.strftime("%Y-%m-%d"),
                }
                arrivals.append(arrival)
            except (ValueError, KeyError) as e:
                logger.warning(f"Failed to parse schedule entry: {e}")
                continue

        return arrivals


class BigQueryWriter:
    """BigQuery writer for MTR arrival data"""

    def __init__(self, project_id: str, dataset_name: str, table_name: str):
        self.client = bigquery.Client(project=project_id)
        self.table_id = f"{project_id}.{dataset_name}.{table_name}"
        self.schema = [
            bigquery.SchemaField("arrival_id", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("line_code", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("line_name", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("station_code", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("dest_station", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("platform", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("sequence", "INTEGER", mode="NULLABLE"),
            bigquery.SchemaField("arrival_time", "TIMESTAMP", mode="NULLABLE"),
            bigquery.SchemaField("time_remaining", "INTEGER", mode="NULLABLE"),
            bigquery.SchemaField("direction", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("ingestion_timestamp", "TIMESTAMP", mode="NULLABLE"),
            bigquery.SchemaField("ingestion_date", "DATE", mode="NULLABLE"),
        ]
        logger.info(f"Initialized BigQuery writer for {self.table_id}")

    @retry.Retry(predicate=retry.if_exception_type(Exception))
    def insert(self, rows: List[Dict[str, Any]]) -> None:
        errors = self.client.insert_rows_json(self.table_id, rows)
        if errors:
            logger.error(f"Failed to insert rows into BigQuery: {errors}")
        else:
            logger.info(f"Inserted {len(rows)} rows into BigQuery")


def poll_and_publish():
    config = Config()
    mtr_client = MTRClient(config.MTR_API_BASE_URL)
    bq_writer = BigQueryWriter(
        config.PROJECT_ID, config.BIGQUERY_DATASET, config.BIGQUERY_TABLE
    )

    logger.info(f"Starting MTR producer for lines: {config.MTR_LINES}")

    total_inserted = 0
    for line_code in config.MTR_LINES:
        stations = mtr_client.MTR_STATIONS.get(line_code, [])
        if not stations:
            logger.warning(f"No stations defined for line {line_code}")
            continue

        for station_code in stations:
            try:
                schedule_data = mtr_client.get_schedule(line_code, station_code)
                arrivals = mtr_client.parse_arrivals(
                    line_code, station_code, schedule_data
                )

                if arrivals:
                    bq_writer.insert(arrivals)
                    total_inserted += len(arrivals)
                    logger.info(
                        f"Inserted {len(arrivals)} arrivals for {line_code}-{station_code}"
                    )
                else:
                    logger.debug(f"No arrivals found for {line_code}-{station_code}")

                time.sleep(0.1)

            except Exception as e:
                logger.error(f"Error processing {line_code}-{station_code}: {e}")
                continue

    logger.info(f"Total inserted: {total_inserted} arrivals")
    return {"status": "success", "inserted": total_inserted}


def run_continuous():
    config = Config()
    logger.info(f"Starting continuous polling (interval: {config.POLL_INTERVAL}s)")

    while True:
        try:
            poll_and_publish()
        except Exception as e:
            logger.error(f"Polling error: {e}")

        time.sleep(config.POLL_INTERVAL)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--continuous":
        run_continuous()
    else:
        result = poll_and_publish()
        print(json.dumps(result))
