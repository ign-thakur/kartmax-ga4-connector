from __future__ import annotations

from typing import Any


def composite_key(row: list[Any], *, date_idx: int, property_idx: int, source_idx: int) -> tuple[str, str, str]:
    return (
        str(row[date_idx]).strip() if len(row) > date_idx else "",
        str(row[property_idx]).strip() if len(row) > property_idx else "",
        str(row[source_idx]).strip() if len(row) > source_idx else "",
    )


def upsert_data_rows(
    existing: list[list[Any]],
    incoming: list[list[Any]],
    *,
    date_idx: int = 0,
    property_idx: int = 1,
    source_idx: int = 2,
) -> tuple[list[list[Any]], int, int]:
    """Merge incoming rows by Date + Property ID + Source. Returns rows, updated, inserted."""
    rows = [list(r) for r in existing]
    index: dict[tuple[str, str, str], int] = {}
    for i, row in enumerate(rows):
        key = composite_key(row, date_idx=date_idx, property_idx=property_idx, source_idx=source_idx)
        if key[0] and key[1] and key[2]:
            index[key] = i

    updated = 0
    inserted = 0
    for nrow in incoming:
        key = composite_key(nrow, date_idx=date_idx, property_idx=property_idx, source_idx=source_idx)
        if not all(key):
            continue
        if key in index:
            rows[index[key]] = nrow
            updated += 1
        else:
            index[key] = len(rows)
            rows.append(nrow)
            inserted += 1
    return rows, updated, inserted