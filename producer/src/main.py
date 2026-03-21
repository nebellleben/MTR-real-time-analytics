"""
MTR API Producer - fetches real-time MTR arrival data and publishes to Pub/Sub.
"""

import os
import json
import time
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, List

from google.cloud import pubsub_v1
from google.api_core import retry
import requests
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Config:
    PROJECT_ID = os.getenv("PROJECT_ID", "your-project-id")
    PUBSUB_TOPIC = os.getenv("PUBSUB_TOPIC", "mtr-arrivals")
    MTR_API_BASE_URL = os.getenv(
        "MTR_API_BASE_URL", "https://rt.data.gov.hk/v1/transport/mtr"
    )
    POLL_INTERVAL = int(os.getenv("POLL_INTERVAL_SECONDS", "30"))
    DELAY_THRESHOLD = int(os.getenv("DELAY_THRESHOLD_SECONDS", "300"))
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

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/json",
            }
        )

    def get_schedule(self, line_code: str) -> List[Dict[str, Any]]:
        """Get train schedule for a specific line"""
        try:
            url = f"{self.base_url}/getSchedule.php?line={line_code}"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data if isinstance(data, list) else []
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch schedule for {line_code}: {e}")
            return []

    def parse_arrivals(
        self, line_code: str, schedule_data: List[Dict]
    ) -> List[Dict[str, Any]]:
        """Parse schedule data into arrival records"""
        arrivals = []
        now = datetime.utcnow()

        for station_data in schedule_data:
            station_code = station_data.get("station", "")
            station_name = station_data.get("name", "")

            for direction in ["UP", "DOWN"]:
                schedules = station_data.get(direction, [])
                for schedule in schedules:
                    try:
                        arrival_time_str = schedule.get("time", "")
                        if not arrival_time_str:
                            continue

                        arrival_time = datetime.strptime(
                            f"{now.strftime('%Y-%m-%d')} {arrival_time_str}",
                            "%Y-%m-%d %H:%M",
                        )

                        time_remaining = int((arrival_time - now).total_seconds())
                        if time_remaining < 0:
                            continue

                        is_delayed = time_remaining > Config.DELAY_THRESHOLD
                        delay_seconds = (
                            time_remaining - Config.DELAY_THRESHOLD if is_delayed else 0
                        )

                        arrival = {
                            "arrival_id": str(uuid.uuid4()),
                            "line_code": line_code,
                            "line_name": self.MTR_LINE_NAMES.get(line_code, "Unknown"),
                            "station_code": station_code,
                            "station_name": station_name,
                            "dest_station": schedule.get("dest", ""),
                            "platform": schedule.get("plat", ""),
                            "sequence": schedule.get("seq", 0),
                            "arrival_time": arrival_time.isoformat(),
                            "time_remaining": time_remaining,
                            "is_delayed": is_delayed,
                            "delay_seconds": delay_seconds,
                            "ingestion_timestamp": now.isoformat(),
                            "ingestion_date": now.strftime("%Y-%m-%d"),
                        }
                        arrivals.append(arrival)
                    except (ValueError, KeyError) as e:
                        logger.warning(f"Failed to parse schedule entry: {e}")
                        continue

        return arrivals


class PubSubPublisher:
    """Pub/Sub publisher for MTR arrival data"""

    def __init__(self, project_id: str, topic_name: str):
        self.publisher = pubsub_v1.PublisherClient()
        self.topic_path = self.publisher.topic_path(project_id, topic_name)
        logger.info(f"Initialized Pub/Sub publisher for {self.topic_path}")

    @retry.Retry(predicate=retry.if_exception_type(Exception))
    def publish(self, message: Dict[str, Any]) -> str:
        """Publish a message to Pub/Sub"""
        data = json.dumps(message).encode("utf-8")
        future = self.publisher.publish(self.topic_path, data)
        message_id = future.result()
        return message_id

    def publish_batch(self, messages: List[Dict[str, Any]]) -> int:
        """Publish multiple messages"""
        count = 0
        for message in messages:
            try:
                message_id = self.publish(message)
                logger.debug(f"Published message {message_id}")
                count += 1
            except Exception as e:
                logger.error(f"Failed to publish message: {e}")
        return count


def poll_and_publish():
    """Main polling loop"""
    config = Config()
    mtr_client = MTRClient(config.MTR_API_BASE_URL)
    pubsub_publisher = PubSubPublisher(config.PROJECT_ID, config.PUBSUB_TOPIC)

    logger.info(f"Starting MTR producer for lines: {config.MTR_LINES}")

    total_published = 0
    for line_code in config.MTR_LINES:
        try:
            schedule_data = mtr_client.get_schedule(line_code)
            arrivals = mtr_client.parse_arrivals(line_code, schedule_data)

            if arrivals:
                published = pubsub_publisher.publish_batch(arrivals)
                total_published += published
                logger.info(f"Published {published} arrivals for {line_code}")
            else:
                logger.info(f"No arrivals found for {line_code}")

        except Exception as e:
            logger.error(f"Error processing line {line_code}: {e}")
            continue

    logger.info(f"Total published: {total_published} arrivals")
    return {"status": "success", "published": total_published}


def run_continuous():
    """Run continuous polling loop"""
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
