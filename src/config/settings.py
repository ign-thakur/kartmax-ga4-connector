import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "output"

load_dotenv(PROJECT_ROOT / ".env")


def get_credentials_path() -> Path:
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not credentials_path:
        raise ValueError("GOOGLE_APPLICATION_CREDENTIALS is not set.")
    resolved = PROJECT_ROOT / credentials_path
    if not resolved.exists():
        raise FileNotFoundError("Google service account credentials not found.")
    return resolved


def get_property_id() -> str:
    property_id = os.getenv("GA4_PROPERTY_ID")
    if not property_id:
        raise ValueError("GA4_PROPERTY_ID is not set.")
    return property_id.strip()


def get_reporting_timezone() -> str:
    """IANA timezone matching the GA4 property reporting timezone."""
    return os.getenv("GA4_REPORTING_TIMEZONE", "UTC").strip()