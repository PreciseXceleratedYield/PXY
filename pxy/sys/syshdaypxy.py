"""Daily cached NSE F&O trading-holiday calendar."""

import json
import logging
from datetime import date, datetime
from pathlib import Path
from threading import Lock
from urllib.error import URLError
from urllib.request import Request, urlopen


NSE_TRADING_HOLIDAY_URL = "https://www.nseindia.com/api/holiday-master?type=trading"
HOLIDAY_CACHE_PATH = Path.home() / ".pxy" / "cache" / "nse_fo_holidays.json"
REQUEST_TIMEOUT_SECONDS = 5
_LOGGER = logging.getLogger(__name__)
_CACHE_LOCK = Lock()
_MEMORY_CACHE = {}


def _parse_holidays(payload):
    try:
        data = json.loads(payload)
        rows = data["FO"]
        holidays = frozenset(
            datetime.strptime(row["tradingDate"], "%d-%b-%Y").date()
            for row in rows
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise ValueError("NSE holiday response has an unexpected format.") from error

    if not holidays:
        raise ValueError("NSE holiday response contains no F&O holidays.")
    return holidays


def _fetch_holidays():
    request = Request(
        NSE_TRADING_HOLIDAY_URL,
        headers={
            "Accept": "application/json",
            "Referer": "https://www.nseindia.com/",
            "User-Agent": "Mozilla/5.0 (compatible; PXY/1.0)",
        },
    )
    with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        return _parse_holidays(response.read())


def _read_cache():
    try:
        data = json.loads(HOLIDAY_CACHE_PATH.read_text(encoding="utf-8"))
        fetched_on = date.fromisoformat(data["fetched_on"])
        holidays = frozenset(date.fromisoformat(value) for value in data["holidays"])
    except FileNotFoundError:
        return None, None
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        _LOGGER.warning("Ignoring invalid cached NSE holiday calendar: %s", error)
        return None, None

    if not holidays:
        _LOGGER.warning("Ignoring empty cached NSE holiday calendar.")
        return None, None
    return fetched_on, holidays


def _write_cache(fetched_on, holidays):
    cache_path = HOLIDAY_CACHE_PATH
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = cache_path.with_suffix(f"{cache_path.suffix}.tmp")
    payload = {
        "fetched_on": fetched_on.isoformat(),
        "holidays": sorted(day.isoformat() for day in holidays),
    }
    temporary_path.write_text(json.dumps(payload), encoding="utf-8")
    temporary_path.replace(cache_path)


def get_nse_fo_holidays(today=None):
    """Return NSE F&O holidays, refreshing the persistent cache once per day."""
    today = today or date.today()
    with _CACHE_LOCK:
        memory_entry = _MEMORY_CACHE.get(today)
        if memory_entry is not None:
            return memory_entry

        cached_on, cached_holidays = _read_cache()
        if cached_on == today:
            _MEMORY_CACHE[today] = cached_holidays
            return cached_holidays

        try:
            holidays = _fetch_holidays()
        except (OSError, URLError, TimeoutError, ValueError) as error:
            if cached_holidays is None:
                raise RuntimeError(
                    "Unable to load NSE F&O holidays and no cached calendar is available."
                ) from error
            _LOGGER.warning(
                "NSE holiday refresh failed; using the last successfully cached "
                "calendar from %s: %s",
                cached_on if cached_on else "unknown date",
                error,
            )
            _MEMORY_CACHE[today] = cached_holidays
            return cached_holidays

        try:
            _write_cache(today, holidays)
        except OSError as error:
            _LOGGER.warning("Could not persist NSE holiday calendar cache: %s", error)

        _MEMORY_CACHE[today] = holidays
        return holidays
