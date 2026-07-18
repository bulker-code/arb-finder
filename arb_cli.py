import argparse
from arb_finder import get_active_sports, is_upcoming, get_best_odds_per_outcome, calculate_stakes, log_result

from config import API_KEY
import requests

argument_parser = argparse.ArgumentParser(description="Arbitrage Betting CLI")
argument_parser.add_argument("--regions", nargs='*', default=["au"], help="list of regions to scan (e.g., ['au', 'eu'])")
argument_parser.add_argument("--sports", nargs='*', default=["upcoming"], help="list of sports keys (e.g., ['soccer_epl', 'basketball_nbl'])")
argument_parser.add_argument("--min-profit", type=float, default=0.0, help="Minimum profit threshold for arbitrage opportunities")
argument_parser.add_argument("--total-stake", type=float, default=100.0, help="Total stake amount for betting calculations")
args = argument_parser.parse_args()

for region in args.regions:
    print(f"Scanning region: {region}")
    active_sports = get_active_sports(API_KEY, wanted_sports=args.sports)

    for sport in active_sports:
        print(f"Scanning sport: {sport}")
        response = requests.get(
            f"https://api.the-odds-api.com/v4/sports/{sport}/odds/",
            params={"apiKey": API_KEY, "regions": ",".join(args.regions), "markets": "h2h"}
        )
        odds_data = response.json()
        for event in odds_data:
            if not is_upcoming(event):
                continue  # skip live/finished matches
            best_odds = get_best_odds_per_outcome(event)
            stakes_info = calculate_stakes(best_odds, args.total_stake)
            log_result(sport, event, stakes_info)
            print(stakes_info)
            if stakes_info["is_arb"] and stakes_info["profit"] >= args.min_profit: 
                print(f"Arbitrage opportunity found for {event['home_team']} vs {event['away_team']}: Expected Profit: {stakes_info['profit']:.2f}%")