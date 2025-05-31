import time
import statistics
import asyncio
import logging
from typing import List, Dict

from metrics.prometheus_metrics import (
     QOS_AVAILABILITY, QOS_AVG_RESPONSE_TIME, QOS_P95_RESPONSE_TIME,
    QOS_P99_RESPONSE_TIME, QOS_ERROR_RATE, QOS_REQUEST_RATE,SERVICE_NAME
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ServiceQualityMonitor:
    def __init__(self, availability_window: int = 60 * 5):
        self.response_times: List[float] = []
        self.request_counts: int = 0
        self.error_counts: int = 0
        self.response_time_with_timestamp: List[tuple] = []
        self.error_timestamps: List[float] = []
        self.availability_window = availability_window
        self.last_check_time = time.time()

    def record_request(self, response_time: float, is_error: bool):
        current_time = time.time()
        self.response_times.append(response_time)
        self.response_time_with_timestamp.append((current_time, response_time))
        self.request_counts += 1
        if is_error:
            self.error_counts += 1
            self.error_timestamps.append(current_time)
        # if current_time - self.last_check_time > 60:
        #     self.cleanup_old_data()
        #     self.last_check_time = current_time

    def cleanup_old_data(self):
        cutoff_time = time.time() - self.availability_window
        new_data = [(ts, rt) for ts, rt in self.response_time_with_timestamp if ts >= cutoff_time]
        self.response_time_with_timestamp = new_data
        self.response_times = [rt for _, rt in new_data]

        self.error_timestamps = [ts for ts in self.error_timestamps if ts >= cutoff_time]

        self.error_counts = len(self.error_timestamps)
        self.request_counts = len(new_data)

    def calculate_metrics(self) -> Dict:
        if not self.response_times:
            return {
                "availability": 100.0,
                "average_response_time": 0,
                "p95_response_time": 0,
                "p99_response_time": 0,
                "error_rate": 0,
                "request_rate": 0
                #"latest_errors": []
            }

        availability = 100.0 * (1 - self.error_counts / max(1, self.request_counts))
        avg_response_time = statistics.mean(self.response_times)
        sorted_times = sorted(self.response_times)
        p95_response_time = sorted_times[int(0.95 * len(sorted_times))] if len(sorted_times) >= 20 else sorted_times[-1]
        p99_response_time = sorted_times[int(0.99 * len(sorted_times))] if len(sorted_times) >= 100 else sorted_times[-1]
        error_rate = self.error_counts / max(1, self.request_counts)
        request_rate = self.request_counts / self.availability_window

        return {
            "availability": availability,
            "average_response_time": avg_response_time,
            "p95_response_time": p95_response_time,
            "p99_response_time": p99_response_time,
            "error_rate": error_rate,
            "request_rate": request_rate
        }

qos_monitor = ServiceQualityMonitor()

async def update_qos_metrics_task():
    while True:
        try:
            metrics = qos_monitor.calculate_metrics()
            QOS_AVAILABILITY.labels(service=SERVICE_NAME).set(metrics["availability"])
            QOS_AVG_RESPONSE_TIME.labels(service=SERVICE_NAME).set(metrics["average_response_time"])
            QOS_P95_RESPONSE_TIME.labels(service=SERVICE_NAME).set(metrics["p95_response_time"])
            QOS_P99_RESPONSE_TIME.labels(service=SERVICE_NAME).set(metrics["p99_response_time"])
            QOS_ERROR_RATE.labels(service=SERVICE_NAME).set(metrics["error_rate"])
            QOS_REQUEST_RATE.labels(service=SERVICE_NAME).set(metrics["request_rate"])
            logger.info(f"Updated QoS metrics: {metrics}")
            qos_monitor.cleanup_old_data()
        except Exception as e:
            logger.error(f"Error updating QoS metrics: {str(e)}")
        await asyncio.sleep(15)


