import pytest
from unittest.mock import Mock, patch
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

from src.api_client import MTRClient


from src.config import Config


class TestMTRClient:
    @patch.object
    def mock_config(self):
        return Config(
            mtr_api_base_url="https://test.url",
            mtr_api_key="test-key",
            kafka_bootstrap_servers="kafka:9092",
            kafka_topic="test-topic",
            kafka_client_id="test-client",
            poll_interval_seconds=30,
            delay_threshold_seconds=300,
            bigquery_project="test-project",
            bigquery_dataset="test-dataset",
            bigquery_table="test-table",
            output_path="/tmp/output",
            temp_checkpoint_path="/tmp/checkpoint",
            checkpoint_interval_seconds=60,
            processing_time_seconds=300,
            log_level="INFO",
        )

        
    def test_get_schedule(self, mock_config):
        client = MTRClient(config=mock_config)
        
        response = Mock()
        response.status_code = 200
        response.json.return_value = [
            {
                "line_code": "TCL",
                "station_code": "HOK",
                "station_name": "Hong Kong Station",
                "dest_station": "Tung Chung",
                "platform": "1",
                "sequence": 1,
                "arrival_time": "2024-01-01T12:00:00"
            }
        ]
        
        assert len(response) == 1
        schedule_data = response[0]
        assert schedule_data[0]["line_code"] == "TCL"
        assert schedule_data[0]["station_code"] == "HOK"
        
    @patch.object
    def mock_requests_session(self):
        session = Mock()
        session.get.return_value = response
        
        client._make_request("get_schedule/TCL")
        
        mock_requests_session.return_value = response
        
        result = client.get_schedule("TCL")
        
        assert result == schedule_data
        assert len(result) == 1

        mock_requests_session.assert_called_with(
            "GET",
            f"{mock_config.mtr_api_base_url}/getSchedule/TCL"
            headers={"Content-Type": "application/json"}
        )

        
    def test_get_arrivals(self, mock_config, mock_requests_session):
        client = MTRClient(config=mock_config)
        
        station_response = Mock()
        station_response.status_code = 200
        station_response.json.return_value = [
                {
                    "line_code": "TML",
                    "station_code": "KOW",
                    "station_name": "Kowloon Station",
                    "dest_station": "Tuen Mun",
                    "platform": "1",
                    "sequence": 1,
                    "arrival_time": "2024-01-01T12:05:00"
                }
            ]
        
        response = Mock()
        response.status_code = 200
        response.json.return_value = {"data": station_response}
        
        mock_requests_session.return_value = response
        
        arrivals = client.get_arrivals("TML")
        
        assert len(arrivals) == 1
        assert arrivals[0]["line_code"] == "TML"
        assert arrivals[0]["station_code"] == "KOW"
