# arb-finder

Scans [The Odds API](https://the-odds-api.com/) for Australian sportsbook odds, finds
arbitrage ("arb") opportunities across bookmakers on the h2h (moneyline) market, and
logs every scanned result to a local file.

## How it works

For each sport requested, the scanner:
1. Pulls current h2h odds for every upcoming event from The Odds API for the requested regions.
2. Finds the best available price per outcome across bookmakers, skipping the
   exchanges in `EXCLUDED_BOOKMAKERS` (`unibet`, `betfair_ex_au`).
3. Checks whether the best odds across outcomes imply a total probability under 100%
   (`total_implied < 1`) — if so, it's an arb, and stake sizes are calculated to lock
   in the same profit regardless of outcome.
4. Logs the result (arb or not) and prints any arbs found above your profit threshold.

## Requirements

- Python 3
- [`requests`](https://pypi.org/project/requests/)
- An API key from [the-odds-api.com](https://the-odds-api.com/) (free tier available)

## Setup

1. Install dependencies:
   ```
   pip install requests
   ```
2. Create `config.py` in the repo root with your API key:
   ```python
   API_KEY = "your-odds-api-key"
   ```
   `config.py` is gitignored — never commit your key.

## Usage

Run the CLI with one or more sport keys:

```
python arb_cli.py --sports soccer_epl basketball_nbl --regions au uk --min-profit 1.0 --total-stake 100
```

| Flag | Default | Description |
|---|---|---|
| `--sports` | `upcoming` | Space-separated sport keys (e.g. `soccer_epl`, `basketball_nbl`), or the special value `upcoming` for the next games across all sports. Invalid/inactive keys are dropped. |
| `--regions` | `au` | Space-separated bookmaker regions to query (e.g. `au`, `uk`, `us`, `eu`). |
| `--min-profit` | `0.0` | Minimum expected profit % required before an arb is printed. |
| `--total-stake` | `100.0` | Total amount to split across outcomes when calculating stakes. |

Only arbs at or above `--min-profit` are printed as opportunities; every scanned event
is still logged regardless of outcome.

## Logging

Every scanned event is appended as one JSON object per line to `arb_log.jsonl`
(JSON Lines format — safe to append to without rewriting the file, and safe to read
back line by line). Each record includes:

```json
{
  "logged_at": "2026-07-19T02:41:40.028889+00:00",
  "sport": "soccer_epl",
  "home_team": "...",
  "away_team": "...",
  "commence_time": "...",
  "is_arb": false,
  "total_implied": 1.0465686274509804,
  "profit": null,
  "odds": { "...": ["price", "bookmaker", "stake (if arb)"] }
}
```

`arb_log.jsonl` is gitignored — it's local run data, not source.

## Notes

- Only the `h2h` (moneyline) market is scanned; totals/spreads aren't covered.
- Live bets have been excluded as odds change too frequently and live bets must be placed by phone in Australia.
- `unibet`, `betfair_ex_au`, and `betfair_ex_eu` are excluded from odds comparison.
- Consider odds may change during the time of scanning and bet placement.
- Most arb opportunities are slim within 1-3% profit
