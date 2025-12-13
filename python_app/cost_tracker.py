import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict


logger = logging.getLogger(__name__)


@dataclass
class UsageRecord:
    month: str
    characters: int
    estimated_cost: float


class CostTracker:
    """Persist character usage and estimated cost per month."""

    def __init__(self, output_dir: Path, price_per_million_chars: float) -> None:
        self.output_dir = Path(output_dir)
        self.price_per_million_chars = price_per_million_chars

    def record(self, char_count: int) -> UsageRecord:
        if char_count <= 0:
            return UsageRecord(month=self._month_key(), characters=0, estimated_cost=0.0)

        self.output_dir.mkdir(parents=True, exist_ok=True)
        month = self._month_key()
        path = self.output_dir / f"{month}.json"

        data: Dict[str, object] = {
            "month": month,
            "characters": 0,
            "estimated_cost": 0.0,
        }

        if path.is_file():
            try:
                existing = json.loads(path.read_text(encoding="utf-8"))
                data.update(existing)
            except Exception:  # pragma: no cover - corrupt files fall back to reset
                logger.warning("Failed to parse existing cost file %s; resetting", path)

        data["characters"] = int(data.get("characters", 0)) + int(char_count)
        data["estimated_cost"] = round(
            (data["characters"] / 1_000_000) * self.price_per_million_chars, 4
        )

        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info(
            "Updated usage for %s: %s chars (est. cost %.4f) -> %s",
            month,
            data["characters"],
            data["estimated_cost"],
            path,
        )

        return UsageRecord(
            month=month,
            characters=int(data["characters"]),
            estimated_cost=float(data["estimated_cost"]),
        )

    @staticmethod
    def _month_key() -> str:
        return datetime.utcnow().strftime("%Y-%m")
