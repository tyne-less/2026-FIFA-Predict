import json
from datetime import datetime, timezone
from pathlib import Path


def save_provider_cache(data: list[dict], path: str, provider: str = "sporttery") -> None:
    cache_path = Path(path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "provider": provider,
        "data": data,
    }
    cache_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_provider_cache(path: str) -> list[dict] | None:
    cache_path = Path(path)
    if not cache_path.exists():
        return None
    payload = json.loads(cache_path.read_text(encoding="utf-8"))
    data = payload.get("data")
    return data if isinstance(data, list) else None


def is_cache_fresh(path: str, max_age_seconds: int = 300) -> bool:
    cache_path = Path(path)
    if not cache_path.exists():
        return False
    payload = json.loads(cache_path.read_text(encoding="utf-8"))
    fetched_at = payload.get("fetched_at")
    if not fetched_at:
        return False
    timestamp = datetime.fromisoformat(fetched_at)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - timestamp).total_seconds() <= max_age_seconds

