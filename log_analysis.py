import json
from arb_logic import LOG_PATH 

def analyse_log():
    try:
        with open(LOG_PATH, 'r') as file:
            count = 0
            arbs_found = 0
            arb_profits = []
            
            for line in file:
                log_entry = json.loads(line)
                # Process the log entry as needed
                if log_entry['is_arb']:
                    arb_profits.append(log_entry['profit'])
                    arbs_found += 1
                count += 1
    except FileNotFoundError:
        print("Log file not found.")
        return
    except json.JSONDecodeError:
        print("Error decoding JSON from log file.")
        return

    if arb_profits:
        average_profit = sum(arb_profits) / len(arb_profits) 
    else:
        average_profit = 0
        
    arb_frequency = arbs_found / count if count > 0 else 0
    print(f"Arbitrage frequency: {arb_frequency:.2%}")
    print(f"Total log entries processed: {count}")
    print(f"Arbs opportunities: {arbs_found}")
    print(f"Average profit:{average_profit:.2f}%")

if __name__ == "__main__":
    analyse_log()