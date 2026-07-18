import requests
from datetime import datetime, timezone
from config import API_KEY
import json
import argparse

EXCLUDED_BOOKMAKERS = {"unibet", "betfair_ex_au", "betfair_ex_eu"}
LOG_PATH = "arb_log.jsonl"

def is_upcoming(event):
    commence = datetime.fromisoformat(event["commence_time"].replace("Z", "+00:00"))
    return commence > datetime.now(timezone.utc)

def get_best_odds_per_outcome(event):
    best_prices = {}
    for bookmaker in event["bookmakers"]:
        if bookmaker["key"] in EXCLUDED_BOOKMAKERS:
            continue
        for market in bookmaker["markets"]:
            if market["key"] != "h2h":
                continue
            for outcome in market["outcomes"]:
                name = outcome["name"]
                price = outcome["price"]
                if name not in best_prices or price > best_prices[name][0]:
                    best_prices[name] = [price, bookmaker["title"]]
    return best_prices


def calculate_stakes(best_odds, total_stake):

    if not best_odds:  # empty dict - no odds available at all
        return {"is_arb": False, "odds": best_odds, "total_implied": None, "profit": None}
    
    odds_list = [value[0] for value in best_odds.values()]
    implied_probs = [1/o for o in odds_list]
    total_implied = sum(implied_probs)
    
    if total_implied < 1:   
        stakes = [(total_stake * p) / total_implied for p in implied_probs]
        expected_profit = (1/total_implied -1)*100
        
        for index, key, in enumerate(best_odds.keys()):
            best_odds[key].append(stakes[index])
        #print(f"Stakes: {[f'{stake:.2f}' for stake in stakes]}, Total Implied: {total_implied:.4f}, Expected Profit: {expected_profit:.2f}")
        return {"is_arb": True, "odds": best_odds, "total_implied": total_implied, "profit": expected_profit}
    
    else:
        #print(f"Not an arb, Implied: {total_implied:.4f}")
        return {"is_arb": False, "odds": best_odds, "total_implied": total_implied, "profit": None}
    

def get_active_sports(api_key, wanted_sports=None):
    response = requests.get(
        "https://api.the-odds-api.com/v4/sports/",
        params={"apiKey": api_key}
    )
    all_sports = response.json()
    
    active_keys = [s["key"] for s in all_sports if s["active"]]
    
    if wanted_sports is not None:
        # only keep sports you actually care about, that are also active
        # "upcoming" is a virtual key the /odds endpoint accepts directly —
        # it never appears in /sports, so let it through unfiltered
        return [s for s in wanted_sports if s == "upcoming" or s in active_keys]
    
    return active_keys

def log_result(sport, event, bet_details):
    record = {
        "logged_at": datetime.now(timezone.utc).isoformat(),
        "sport": sport,
        "home_team": event["home_team"],
        "away_team": event["away_team"],
        "commence_time": event["commence_time"],
        "is_arb": bet_details["is_arb"],
        "total_implied": bet_details["total_implied"],
        "profit": bet_details["profit"],
        "odds": bet_details["odds"],
    }
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(record) + "\n")