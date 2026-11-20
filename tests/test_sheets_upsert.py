from src.exports.sheets.upsert import upsert_data_rows


def test_upsert_updates_existing_key():
    existing = [
        ["2026-11-18", "352673114", "google", 100, "INR", "2026-11-18", "2026-11-18", "t1"],
    ]
    incoming = [
        ["2026-11-18", "352673114", "google", 200, "INR", "2026-11-01", "2026-11-18", "t2"],
    ]
    merged, updated, inserted = upsert_data_rows(existing, incoming)
    assert updated == 1
    assert inserted == 0
    assert len(merged) == 1
    assert merged[0][3] == 200
    assert merged[0][7] == "t2"


def test_upsert_inserts_new_source():
    existing = [
        ["2026-11-18", "352673114", "google", 100, "INR", "2026-11-18", "2026-11-18", "t1"],
    ]
    incoming = [
        ["2026-11-18", "352673114", "duckduckgo", 4, "INR", "2026-11-18", "2026-11-18", "t2"],
    ]
    merged, updated, inserted = upsert_data_rows(existing, incoming)
    assert updated == 0
    assert inserted == 1
    assert len(merged) == 2
    assert merged[1][2] == "duckduckgo"