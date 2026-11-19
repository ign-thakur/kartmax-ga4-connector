
import os
from pathlib import Path

from dotenv import load_dotenv
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import RunReportRequest, DateRange, Metric

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


def get_ga4_client():
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    property_id = os.getenv("GA4_PROPERTY_ID")

    if not credentials_path or not property_id:
        raise ValueError("GA4 credentials path or Property ID is missing.")

    credentials_file = PROJECT_ROOT / credentials_path

    if not credentials_file.exists():
        raise FileNotFoundError("Google service account credentials not found.")

    client = BetaAnalyticsDataClient.from_service_account_file(
        str(credentials_file)
    )

    return client, property_id


def test_ga4_connection():
    client, property_id = get_ga4_client()

    request = RunReportRequest(
        property=f"properties/{property_id}",
        date_ranges=[DateRange(start_date="yesterday", end_date="yesterday")],
        metrics=[Metric(name="sessions")],
    )

    response = client.run_report(request)

    return response
