import json
from pathlib import Path

import pytest

from arb_logic import calculate_stakes, get_best_odds_per_outcome, is_upcoming, log_result

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "sample_odds_response.json"


@pytest.fixture
def sample_event():
    with open(FIXTURE_PATH) as f:
        events = json.load(f)
    return events[0]


def test_pipeline_parses_real_shaped_api_response(sample_event):
    """
    Guards against The Odds API changing its response shape: if bookmakers/
    markets/outcomes keys move, this breaks loudly here instead of silently
    in production.
    """
    best_odds = get_best_odds_per_outcome(sample_event)

    # betfair_ex_au is excluded, so its 2.50/5.00/3.80 prices must not win
    # even though they're the best on offer
    assert best_odds["Arsenal"] == [2.10, "Sportsbet"]
    assert best_odds["Chelsea"] == [4.20, "TAB"]
    assert best_odds["Draw"] == [3.40, "Sportsbet"]


def test_pipeline_end_to_end_produces_arb_matching_log_schema(sample_event, tmp_path, monkeypatch):
    log_path = tmp_path / "arb_log.jsonl"
    monkeypatch.setattr("arb_logic.LOG_PATH", str(log_path))

    best_odds = get_best_odds_per_outcome(sample_event)
    stakes_info = calculate_stakes(best_odds, total_stake=100.0)
    log_result(sample_event["sport_key"], sample_event, stakes_info)

    assert log_path.exists()
    lines = log_path.read_text().strip().splitlines()
    assert len(lines) == 1

    record = json.loads(lines[0])

    # schema documented in README's "Logging" section
    for field in ("logged_at", "sport", "home_team", "away_team", "commence_time",
                  "is_arb", "total_implied", "profit", "odds"):
        assert field in record

    assert record["sport"] == "soccer_epl"
    assert record["home_team"] == "Arsenal"
    assert record["away_team"] == "Chelsea"
    assert record["is_arb"] == stakes_info["is_arb"]


def test_is_upcoming_handles_real_api_timestamp_format(sample_event):
    # sample_event's commence_time is far in the future relative to any
    # plausible test run date, so this should always evaluate True
    assert is_upcoming(sample_event) is True
