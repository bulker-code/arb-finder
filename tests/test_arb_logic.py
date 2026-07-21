from datetime import datetime, timedelta, timezone

import pytest

from arb_logic import (
    calculate_stakes,
    get_active_sports,
    get_best_odds_per_outcome,
    is_upcoming,
)


# ---------------------------------------------------------------------------
# calculate_stakes
# ---------------------------------------------------------------------------

def test_calculate_stakes_no_odds_available():
    result = calculate_stakes({}, 100.0)

    assert result == {"is_arb": False, "odds": {}, "total_implied": None, "profit": None}


def test_calculate_stakes_finds_arbitrage():
    # 1/2.10 + 1/2.30 = 0.9110... < 1, so this is an arb
    best_odds = {
        "Team A": [2.10, "Book A"],
        "Team B": [2.30, "Book B"],
    }

    result = calculate_stakes(best_odds, 100.0)

    expected_implied = 1 / 2.10 + 1 / 2.30
    expected_profit = (1 / expected_implied - 1) * 100

    assert result["is_arb"] is True
    assert result["total_implied"] == pytest.approx(expected_implied)
    assert result["profit"] == pytest.approx(expected_profit)


def test_calculate_stakes_stakes_sum_to_total_and_are_proportional():
    best_odds = {
        "Team A": [2.10, "Book A"],
        "Team B": [2.30, "Book B"],
    }

    result = calculate_stakes(best_odds, 100.0)
    stakes = [value[2] for value in result["odds"].values()]

    assert sum(stakes) == pytest.approx(100.0)
    # Team A's lower price (2.10) means a higher implied probability than
    # Team B's (2.30), so Team A gets the larger stake.
    assert stakes[0] > stakes[1]


def test_calculate_stakes_no_arbitrage():
    # 1/1.80 + 1/1.80 = 1.111... >= 1, not an arb
    best_odds = {
        "Team A": [1.80, "Book A"],
        "Team B": [1.80, "Book B"],
    }

    result = calculate_stakes(best_odds, 100.0)

    assert result["is_arb"] is False
    assert result["profit"] is None
    assert result["total_implied"] == pytest.approx(1 / 1.80 + 1 / 1.80)
    # non-arb odds are returned without a stake appended
    assert all(len(value) == 2 for value in result["odds"].values())


def test_calculate_stakes_breakeven_is_not_arbitrage():
    # 1/2.0 + 1/2.0 == 1 exactly -> condition is strict "< 1", so not an arb
    best_odds = {
        "Team A": [2.0, "Book A"],
        "Team B": [2.0, "Book B"],
    }

    result = calculate_stakes(best_odds, 100.0)

    assert result["is_arb"] is False
    assert result["total_implied"] == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# get_best_odds_per_outcome
# ---------------------------------------------------------------------------

def _event(bookmakers):
    return {"bookmakers": bookmakers}


def _bookmaker(key, title, outcomes):
    return {
        "key": key,
        "title": title,
        "markets": [{"key": "h2h", "outcomes": outcomes}],
    }


def test_get_best_odds_picks_highest_price_across_bookmakers():
    event = _event([
        _bookmaker("sportsbet", "Sportsbet", [
            {"name": "Team A", "price": 1.90},
            {"name": "Team B", "price": 2.00},
        ]),
        _bookmaker("tab", "TAB", [
            {"name": "Team A", "price": 2.05},
            {"name": "Team B", "price": 1.85},
        ]),
    ])

    best = get_best_odds_per_outcome(event)

    assert best["Team A"] == [2.05, "TAB"]
    assert best["Team B"] == [2.00, "Sportsbet"]


def test_get_best_odds_excludes_excluded_bookmakers():
    event = _event([
        _bookmaker("betfair_ex_au", "Betfair Exchange", [
            {"name": "Team A", "price": 10.0},
        ]),
        _bookmaker("sportsbet", "Sportsbet", [
            {"name": "Team A", "price": 1.90},
        ]),
    ])

    best = get_best_odds_per_outcome(event)

    assert best["Team A"] == [1.90, "Sportsbet"]


def test_get_best_odds_ignores_non_h2h_markets():
    event = _event([
        {
            "key": "sportsbet",
            "title": "Sportsbet",
            "markets": [{"key": "totals", "outcomes": [{"name": "Over", "price": 1.90}]}],
        }
    ])

    best = get_best_odds_per_outcome(event)

    assert best == {}


def test_get_best_odds_keeps_first_seen_on_tie():
    event = _event([
        _bookmaker("sportsbet", "Sportsbet", [{"name": "Team A", "price": 2.00}]),
        _bookmaker("tab", "TAB", [{"name": "Team A", "price": 2.00}]),
    ])

    best = get_best_odds_per_outcome(event)

    # strict ">" comparison means an equal later price does not replace the first
    assert best["Team A"] == [2.00, "Sportsbet"]


def test_get_best_odds_no_bookmakers_returns_empty():
    assert get_best_odds_per_outcome(_event([])) == {}


# ---------------------------------------------------------------------------
# is_upcoming
# ---------------------------------------------------------------------------

def _iso_z(dt):
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def test_is_upcoming_future_event_is_true():
    future = datetime.now(timezone.utc) + timedelta(hours=1)
    event = {"commence_time": _iso_z(future)}

    assert is_upcoming(event) is True


def test_is_upcoming_past_event_is_false():
    past = datetime.now(timezone.utc) - timedelta(hours=1)
    event = {"commence_time": _iso_z(past)}

    assert is_upcoming(event) is False


# ---------------------------------------------------------------------------
# get_active_sports
# ---------------------------------------------------------------------------

class _FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload


def test_get_active_sports_filters_to_wanted_and_active(monkeypatch):
    sports_payload = [
        {"key": "soccer_epl", "active": True},
        {"key": "basketball_nbl", "active": True},
        {"key": "rugby_nrl", "active": False},
    ]

    def fake_get(url, params=None):
        return _FakeResponse(sports_payload)

    monkeypatch.setattr("arb_logic.requests.get", fake_get)

    result = get_active_sports("fake-key", wanted_sports=["soccer_epl", "rugby_nrl"])

    # rugby_nrl is wanted but inactive, so it's dropped
    assert result == ["soccer_epl"]


def test_get_active_sports_upcoming_passes_through_unfiltered(monkeypatch):
    sports_payload = [{"key": "soccer_epl", "active": True}]

    monkeypatch.setattr("arb_logic.requests.get", lambda url, params=None: _FakeResponse(sports_payload))

    result = get_active_sports("fake-key", wanted_sports=["upcoming"])

    assert result == ["upcoming"]


def test_get_active_sports_no_wanted_sports_returns_all_active(monkeypatch):
    sports_payload = [
        {"key": "soccer_epl", "active": True},
        {"key": "rugby_nrl", "active": False},
    ]

    monkeypatch.setattr("arb_logic.requests.get", lambda url, params=None: _FakeResponse(sports_payload))

    result = get_active_sports("fake-key", wanted_sports=None)

    assert result == ["soccer_epl"]


def test_get_active_sports_returns_empty_list_on_non_200(monkeypatch):
    monkeypatch.setattr(
        "arb_logic.requests.get",
        lambda url, params=None: _FakeResponse({"message": "rate limited"}, status_code=429),
    )

    result = get_active_sports("fake-key", wanted_sports=["soccer_epl"])

    assert result == []
