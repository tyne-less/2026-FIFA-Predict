from pathlib import Path

import pytest

from providers.cache import is_cache_fresh, load_provider_cache, save_provider_cache
from providers.csv_provider import CsvProvider
from providers.errors import ProviderUnavailableError
from providers.sporttery_provider import SportteryProvider
from services import live_data_service
from services.live_data_service import get_odds_data


def test_csv_provider_returns_existing_odds_format():
    provider = CsvProvider()

    odds = provider.fetch_odds("F3")

    assert odds["match_id"] == "F3"
    assert odds["normal"]["available"] is True
    assert odds["normal"]["home_odds"] == 1.35
    assert odds["handicap"]["available"] is True
    assert odds["handicap"]["handicap"] == -1


def test_csv_provider_fetch_all_odds_keeps_csv_workflow():
    provider = CsvProvider()

    rows = provider.fetch_all_odds()

    assert {row["match_id"] for row in rows} >= {"F3", "F4"}


def test_provider_cache_round_trip(tmp_path: Path):
    cache_path = tmp_path / "sporttery_odds.json"
    data = [{"match_id": "001"}]

    save_provider_cache(data, str(cache_path), provider="sporttery")

    assert load_provider_cache(str(cache_path)) == data
    assert is_cache_fresh(str(cache_path), max_age_seconds=300)


def test_sporttery_provider_requires_configured_endpoint(monkeypatch):
    monkeypatch.delenv("SPORTTERY_MATCHES_URL", raising=False)
    monkeypatch.delenv("SPORTTERY_ODDS_URL", raising=False)
    provider = SportteryProvider(matches_url=None, odds_url=None)

    with pytest.raises(ProviderUnavailableError):
        provider.fetch_all_odds()


def test_live_data_service_csv_source_returns_metadata():
    result = get_odds_data("csv")

    assert result["source"] == "csv"
    assert result["from_cache"] is False
    assert result["warning"] is None
    assert result["data"]


def test_live_data_service_falls_back_to_cache_on_provider_error(tmp_path: Path, monkeypatch):
    class FailingProvider:
        def fetch_all_odds(self, date=None):
            raise ProviderUnavailableError("offline")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(live_data_service, "_build_provider", lambda provider_name: FailingProvider())
    save_provider_cache([{"match_id": "cached"}], "data/cache/sporttery_odds.json", provider="sporttery")

    result = live_data_service.get_odds_data("sporttery")

    assert result["from_cache"] is True
    assert result["data"] == [{"match_id": "cached"}]
    assert "实时数据暂不可用" in result["warning"]
