import os

import requests

from providers.errors import ProviderParseError, ProviderUnavailableError


class SportteryProvider:
    def __init__(
        self,
        cache_dir: str = "data/cache",
        timeout: int = 10,
        matches_url: str | None = None,
        odds_url: str | None = None,
    ):
        self.cache_dir = cache_dir
        self.timeout = timeout
        self.matches_url = matches_url or os.getenv("SPORTTERY_MATCHES_URL")
        self.odds_url = odds_url or os.getenv("SPORTTERY_ODDS_URL")

    def fetch_matches(self, date: str | None = None) -> list[dict]:
        if not self.matches_url:
            raise ProviderUnavailableError("中国体彩实时比赛接口尚未配置。")
        payload = self._fetch_json(self.matches_url, date)
        return self._parse_matches(payload)

    def fetch_all_odds(self, date: str | None = None) -> list[dict]:
        if not self.odds_url:
            raise ProviderUnavailableError("中国体彩实时赔率接口尚未配置。")
        payload = self._fetch_json(self.odds_url, date)
        return self._parse_odds_list(payload)

    def fetch_odds(self, match_id: str) -> dict | None:
        odds = self.fetch_all_odds()
        for item in odds:
            if item.get("match_id") == match_id:
                return item
        return None

    def _fetch_json(self, url: str, date: str | None) -> dict | list:
        params = {"date": date} if date else None
        try:
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as error:
            raise ProviderUnavailableError(f"中国体彩实时数据请求失败：{error}") from error
        except ValueError as error:
            raise ProviderParseError("中国体彩实时接口未返回有效 JSON。") from error

    def _parse_matches(self, payload: dict | list) -> list[dict]:
        items = _extract_items(payload)
        matches = []
        for item in items:
            match_id = _first(item, "match_id", "matchId", "id", "mid")
            home = _first(item, "home", "homeTeam", "home_team", "h_cn")
            away = _first(item, "away", "awayTeam", "away_team", "a_cn")
            if not match_id or not home or not away:
                raise ProviderParseError("中国体彩比赛数据缺少 match_id/home/away 字段。")
            matches.append(
                {
                    "match_id": str(match_id),
                    "match_code": _first(item, "match_code", "matchCode", "num", "matchNum"),
                    "league": _first(item, "league", "leagueName", "competition"),
                    "kickoff_time": _first(item, "kickoff_time", "kickoffTime", "matchTime"),
                    "home": home,
                    "away": away,
                    "status": _first(item, "status", "matchStatus", "saleStatus"),
                    "sale_status": _first(item, "sale_status", "saleStatus"),
                    "supports_single": bool(_first(item, "supports_single", "single", "isSingle")),
                }
            )
        return matches

    def _parse_odds_list(self, payload: dict | list) -> list[dict]:
        items = _extract_items(payload)
        odds_rows = []
        for item in items:
            match_id = _first(item, "match_id", "matchId", "id", "mid")
            home = _first(item, "home", "homeTeam", "home_team", "h_cn")
            away = _first(item, "away", "awayTeam", "away_team", "a_cn")
            normal = item.get("normal") or item.get("spf") or {}
            handicap = item.get("handicap") or item.get("rqspf") or {}
            if not match_id or not home or not away:
                raise ProviderParseError("中国体彩赔率数据缺少 match_id/home/away 字段。")
            odds_rows.append(
                {
                    "match_id": str(match_id),
                    "match_code": _first(item, "match_code", "matchCode", "num", "matchNum"),
                    "home": home,
                    "away": away,
                    "last_update": _first(item, "last_update", "lastUpdate", "updateTime"),
                    "normal": _parse_normal_odds(normal),
                    "handicap": _parse_handicap_odds(handicap),
                }
            )
        return odds_rows


def _extract_items(payload: dict | list) -> list[dict]:
    # Official endpoint discovery belongs here; keep endpoint-specific reshaping isolated.
    if isinstance(payload, list):
        return payload
    for key in ("data", "matches", "odds", "list", "result"):
        value = payload.get(key)
        if isinstance(value, list):
            return value
    raise ProviderParseError("中国体彩接口结构无法识别。")


def _parse_normal_odds(data: dict) -> dict:
    if not data:
        return {"available": False}
    try:
        odds = {
            "available": bool(data),
            "home_odds": _float_or_none(_first(data, "home_odds", "home", "win", "h")),
            "draw_odds": _float_or_none(_first(data, "draw_odds", "draw", "d")),
            "away_odds": _float_or_none(_first(data, "away_odds", "away", "loss", "a")),
        }
        if None in (odds["home_odds"], odds["draw_odds"], odds["away_odds"]):
            raise ProviderParseError("中国体彩普通胜平负赔率字段不完整。")
        return odds
    except (TypeError, ValueError) as error:
        raise ProviderParseError("中国体彩普通胜平负赔率格式无法解析。") from error


def _parse_handicap_odds(data: dict) -> dict:
    if not data:
        return {"available": False}
    try:
        odds = {
            "available": bool(data),
            "handicap": _int_or_none(_first(data, "handicap", "line", "rq")),
            "handicap_home_odds": _float_or_none(_first(data, "handicap_home_odds", "home", "win", "h")),
            "handicap_draw_odds": _float_or_none(_first(data, "handicap_draw_odds", "draw", "d")),
            "handicap_away_odds": _float_or_none(_first(data, "handicap_away_odds", "away", "loss", "a")),
        }
        if None in (
            odds["handicap"],
            odds["handicap_home_odds"],
            odds["handicap_draw_odds"],
            odds["handicap_away_odds"],
        ):
            raise ProviderParseError("中国体彩让球胜平负赔率字段不完整。")
        return odds
    except (TypeError, ValueError) as error:
        raise ProviderParseError("中国体彩让球胜平负赔率格式无法解析。") from error


def _first(data: dict, *keys: str):
    for key in keys:
        if key in data and data[key] not in ("", None):
            return data[key]
    return None


def _float_or_none(value) -> float | None:
    return None if value is None else float(value)


def _int_or_none(value) -> int | None:
    return None if value is None else int(value)
