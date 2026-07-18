import requests
from datetime import datetime, timezone
from config import API_KEY
import json

EXCLUDED_BOOKMAKERS = {"unibet", "betfair_ex_au", "betfair_ex_eu"}
LOG_PATH = "arb_log.jsonl"


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
    
def merge_responses(au_data, eu_data):
    # Build a lookup from the EU data keyed by (home_team, away_team, commence_time)
    eu_lookup = {}
    for event in eu_data:
        key = (event['home_team'], event['away_team'], event['commence_time'])
        eu_lookup[key] = event.get('bookmakers', [])
    
    # Merge EU bookmakers into AU events where there's a match
    merged = []
    for event in au_data:
        key = (event['home_team'], event['away_team'], event['commence_time'])
        if key in eu_lookup:
            event['bookmakers'] = event.get('bookmakers', []) + eu_lookup[key]
        merged.append(event)
    
    return merged


def get_active_sports(api_key, wanted_sports=None):
    response = requests.get(
        "https://api.the-odds-api.com/v4/sports/",
        params={"apiKey": api_key}
    )
    all_sports = response.json()
    
    active_keys = [s["key"] for s in all_sports if s["active"]]
    
    if wanted_sports is not None:
        # only keep sports you actually care about, that are also active
        return [s for s in wanted_sports if s in active_keys]
    
    return active_keys

my_sports_of_interest = ["soccer_epl", "rugbyleague_nrl", "aussierules_afl"]
sports_to_scan = get_active_sports(API_KEY, wanted_sports=my_sports_of_interest)
print(sports_to_scan)

#sports_to_scan = ["upcoming"]


MIN_PROFIT_THRESHOLD = 0.0

for sport in sports_to_scan:
    au_response = requests.get(
        f"https://api.the-odds-api.com/v4/sports/{sport}/odds/",
        params={"apiKey": API_KEY, "regions": "au", "markets": "h2h"}
    )
    data = au_response.json()


    if not isinstance(data, list):
        print(f"Unexpected response for {sport}: {data}")
        continue
          
    for event in data:
        if not is_upcoming(event):
            continue  # skip live/finished matches
        best_odds = get_best_odds_per_outcome(event)
        bet_details = calculate_stakes(best_odds, 100)
        log_result(sport, event, bet_details)
        print(bet_details)
        if bet_details["is_arb"] and bet_details["profit"] >= MIN_PROFIT_THRESHOLD:
            print(f"ARB FOUND — Profit: {bet_details['profit']:.2f}%")
            for name, (price, book, stake) in bet_details["odds"].items():
                print(f"  {name}: {price:.2f} @ {book} — stake ${stake:.2f}")
  
