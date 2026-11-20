"""Shared GA4 run_report parameters for KartmaX source reports."""

from __future__ import annotations

DATE_DIMENSION = "date"
SOURCE_DIMENSION = "sessionSource"

REPORT_LIMIT = 100_000

GMV_METRIC = "grossPurchaseRevenue"
SESSIONS_METRIC = "sessions"

SOURCE_REPORT_DIMENSIONS = [DATE_DIMENSION, SOURCE_DIMENSION]