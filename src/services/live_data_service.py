from providers.cache import load_provider_cache, save_provider_cache
from providers.csv_provider import CsvProvider
from providers.errors import ProviderError
from providers.sporttery_provider import SportteryProvider


def get_odds_data(
    provider_name: str,
    date: str | None = None,
    use_cache: bool = True,
    cache_ttl_seconds: int = 300,
) -> dict:
    provider = _build_provider(provider_name)
    cache_path = f"data/cache/{provider_name}_odds.json"

    if provider_name == "csv":
        return {
            "data": provider.fetch_all_odds(date),
            "source": "csv",
            "from_cache": False,
            "warning": None,
        }

    try:
        data = provider.fetch_all_odds(date)
    except ProviderError as error:
        cached = load_provider_cache(cache_path) if use_cache else None
        if cached is not None:
            return {
                "data": cached,
                "source": provider_name,
                "from_cache": True,
                "warning": f"实时数据暂不可用，已使用缓存数据：{error}",
            }
        raise

    if use_cache:
        save_provider_cache(data, cache_path, provider=provider_name)
    return {
        "data": data,
        "source": provider_name,
        "from_cache": False,
        "warning": None,
    }


def _build_provider(provider_name: str):
    if provider_name == "csv":
        return CsvProvider()
    if provider_name == "sporttery":
        return SportteryProvider()
    raise ValueError(f"unknown provider_name: {provider_name}")
