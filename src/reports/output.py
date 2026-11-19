import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config.settings import OUTPUT_DIR

logger = logging.getLogger(__name__)


def build_report_payload(
    *,
    property_id: str,
    report_type: str,
    start_date: str,
    end_date: str,
    data: list[dict[str, Any]],
    currency: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "property_id": property_id,
        "report_type": report_type,
        "start_date": start_date,
        "end_date": end_date,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "data": data,
    }
    if currency is not None:
        payload["currency"] = currency
    return payload


def write_report_json(payload: dict[str, Any], filename_stem: str) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    end_label = payload["end_date"].replace("-", "")
    path = OUTPUT_DIR / f"{filename_stem}_{end_label}.json"
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
    logger.info("Wrote report to %s", path)
    return path


def validate_report_rows(
    rows: list[dict[str, Any]],
    *,
    metric_key: str,
    expect_currency: bool,
    currency: str | None,
) -> None:
    if not rows:
        raise ValueError("GA4 returned no data rows for the requested range.")

    for row in rows:
        if not row.get("date"):
            raise ValueError("Row missing date dimension.")
        if "channel" not in row:
            raise ValueError("Row missing channel dimension.")
        raw = row.get(metric_key)
        if raw is None:
            raise ValueError(f"Row missing metric '{metric_key}'.")
        try:
            float(raw)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Non-numeric {metric_key}: {raw!r}") from exc

    if expect_currency and not currency:
        logger.warning("GMV report has no currency_code in GA4 metric metadata.")