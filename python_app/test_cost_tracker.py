from datetime import datetime
from pathlib import Path

from .cost_tracker import CostTracker


class _FixedDatetime(datetime):
    @classmethod
    def utcnow(cls):  # pragma: no cover - used for determinism
        return datetime(2024, 1, 15, 12, 0, 0)


def test_cost_tracker_records_monthly(tmp_path, monkeypatch):
    # Pin the date for deterministic file naming
    monkeypatch.setattr("python_app.cost_tracker.datetime", _FixedDatetime)

    tracker = CostTracker(tmp_path, price_per_million_chars=10.0)

    record1 = tracker.record(1000)
    assert record1.characters == 1000
    assert record1.estimated_cost == 0.01
    assert record1.month == "2024-01"

    record2 = tracker.record(500)
    assert record2.characters == 1500
    assert record2.estimated_cost == 0.015
    assert record2.month == "2024-01"

    cost_file = Path(tmp_path) / f"{record2.month}.json"
    content = cost_file.read_text(encoding="utf-8")
    assert "estimated_cost" in content
