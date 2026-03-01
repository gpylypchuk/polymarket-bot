import os, json, time, requests, threading, websocket, csv
from datetime import datetime, timezone
from dotenv import load_dotenv
from collections import deque

load_dotenv()

price_buffer = deque(maxlen=3)
btc_price_live = 0.0

def on_message(ws, message):
    global btc_price_live
    price = float(json.loads(message)['c'])
    btc_price_live = price
    price_buffer.append(price)

def run_binance_ws():
    ws = websocket.WebSocketApp("wss://stream.binance.com:9443/ws/btcusdt@ticker", on_message=on_message)
    ws.run_forever()

threading.Thread(target=run_binance_ws, daemon=True).start()

fast_session = requests.Session()
fast_session.headers.update({'User-Agent': 'Mozilla/5.0'})

def get_raw_best_prices(token_id):
    try:
        res = fast_session.get(f"https://clob.polymarket.com/book?token_id={token_id}", timeout=2).json()
        best_bid = max(float(b['price']) for b in res['bids']) if res.get('bids') else None
        best_ask = min(float(a['price']) for a in res['asks']) if res.get('asks') else None
        return best_bid, best_ask
    except:
        return None, None

MAX_TESTS = 200
test_count = 0
simulated_balance = 0.0
wins = 0
losses = 0

csv_filename = os.path.join("logs", "full_exit_probe_log.csv")
os.makedirs("logs", exist_ok=True)

if not os.path.exists(csv_filename):
    with open(csv_filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Timestamp", "Slot", "Outcome", "Shares", "Entry_Price", "Target_Price", "Exit_Price", "Max_Bid_Seen", "Profit_USDC", "Status"])

def log_trade(slot, outcome, shares, entry_price, target, exit_price, max_bid, profit, status):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(csv_filename, mode='a', newline='') as f:
        csv.writer(f).writerow([timestamp, slot, outcome, round(shares, 2), entry_price, target, exit_price, max_bid, round(profit, 4), status])

print("=======================================")
print(f"🧪 PAPER TRADING | BOT: FULL EXIT PROBE")
print(f"🎯 Entry: 0.01 - 0.02 | Zones: 25-70 / 40-100")
print("⚡ Full Exit: TP 0.25 (Continuous Monitoring)")
print("=======================================\n")

while test_count < MAX_TESTS:
    now_ts = int(time.time())
    start_slot = (now_ts // 300) * 300
    slug = f"btc-updown-5m-{start_slot}"
    
    try:
        r = requests.get(f"https://gamma-api.polymarket.com/events?slug={slug}")
        event_data = r.json()
        if not event_data: time.sleep(10); continue
        
        market = event_data[0]["markets"][0]
        clob_ids = json.loads(market["clobTokenIds"])
        end_date = datetime.fromisoformat(market.get("endDate").replace("Z", "+00:00"))
        
        start_time_ms = int(datetime.fromisoformat(event_data[0].get("startTime", "")).timestamp() * 1000)
        k_res = requests.get(f"https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=5m&startTime={start_time_ms}&limit=1")
        p_strike = float(k_res.json()[0][1])
        print(f"\n📍 [SLOT {start_slot}] Strike: ${p_strike}")
    except:
        time.sleep(5); continue

    market_active = True
    trade_open = False 
    has_sold = False
    secured_profit = 0.0
    actual_exit_price = 0.0

    while market_active:
        try:
            seconds_left = (end_date - datetime.now(timezone.utc)).total_seconds()

            if seconds_left <= 0:
                if trade_open:
                    if has_sold:
                        print(f"🏁 CLOSE | Secured profit: ${secured_profit:.2f} | Real Max Bid Reached: ${max_bid_seen:.2f}")
                        log_trade(start_slot, token_outcome, sim_shares, sim_entry_price, target_scalp, actual_exit_price, max_bid_seen, secured_profit, "FULL_PROFIT")
                        test_count += 1
                    else:
                        # If not sold, we win or lose at the Oracle (as usual)
                        win = (token_outcome == "Up" and btc_price_live >= p_strike) or \
                              (token_outcome == "Down" and btc_price_live < p_strike)
                        final_price = 1.00 if win else 0.00
                        profit = (final_price * sim_shares) - sim_cost
                        simulated_balance += profit
                        if win: wins += 1
                        else: losses += 1
                        
                        status = "WIN_ORACLE" if win else "LOSS_ORACLE"
                        print(f"{'🏆' if win else '💀'} ORACLE RESULT: {status} | Profit: ${profit:.2f} | Max Bid Seen: ${max_bid_seen:.2f}")
                        log_trade(start_slot, token_outcome, sim_shares, sim_entry_price, target_scalp, final_price, max_bid_seen, profit, status)
                        test_count += 1
                market_active = False; break

            # A. STATE: LOOKING FOR ENTRY
            if not trade_open:
                extreme_hot_zone = (0 < seconds_left <= 45) and all(40 < abs(p - p_strike) < 100 for p in price_buffer)
                normal_hot_zone = (0 < seconds_left <= 20) and all(25 < abs(p - p_strike) < 70 for p in price_buffer)

                if extreme_hot_zone or normal_hot_zone:
                    trend_up = all((p - p_strike) > 0 for p in price_buffer)
                    target_outcome = "Down" if trend_up else "Up" 
                    target_token_id = clob_ids[1] if trend_up else clob_ids[0]

                    _, best_ask = get_raw_best_prices(target_token_id)

                    if best_ask:
                        if int(seconds_left * 10) % 20 == 0:
                            diff = btc_price_live - p_strike
                            print(f"🔍 [BLACK SWAN] BTC Diff: ${diff:.2f} | Evaluating counter-trade ({target_outcome}) at ${best_ask:.2f}")

                        if 0.01 <= best_ask <= 0.02:
                            sim_entry_price = best_ask
                            sim_shares = 20.0  
                            sim_cost = sim_shares * sim_entry_price
                            
                            target_scalp = 0.25      # Target for full sale
                            max_bid_seen = 0.0 

                            print(f"\n🚀 [FULL ENTRY] Buying {sim_shares} shares of {target_outcome} at ${sim_entry_price:.2f}")
                            print(f"🎯 SINGLE TARGET: ${target_scalp:.2f} (Full Sale)")
                            
                            trade_open = True
                            active_token = target_token_id 
                            token_outcome = target_outcome
                            
                        elif best_ask > 0.02:
                            if int(seconds_left * 10) % 20 == 0: print(f"⚠️ [STALKING] Counter-trade too expensive (${best_ask:.2f}). Waiting for 0.02...")
                
                elif int(seconds_left) % 10 == 0:
                    print(f"⏳ {int(seconds_left)}s to close. BTC: ${btc_price_live:.2f} | Diff: ${abs(btc_price_live - p_strike):.2f}")
                
                time.sleep(0.1) 

            # B. STATE: MONITORING EXIT
            elif trade_open:
                current_bid, _ = get_raw_best_prices(active_token)
                
                if current_bid:
                    if current_bid > max_bid_seen:
                        max_bid_seen = current_bid
                
                # FULL SALE IF HITS 0.25
                if not has_sold and current_bid and current_bid >= target_scalp:
                    secured_profit = (current_bid * sim_shares) - sim_cost
                    simulated_balance += secured_profit
                    wins += 1 
                    
                    has_sold = True
                    actual_exit_price = current_bid
                    
                    print(f"\n💸 SUCCESSFUL PANIC SCALP! Sold at ${current_bid:.2f} | Profit: +${secured_profit:.2f}")
                    print(f"👀 Monitoring Order Book until the end to record the true ceiling...")
                    
                    # Now the bot keeps looping, updating max_bid_seen.
                    
                else:
                    if not has_sold and int(seconds_left * 10) % 20 == 0:
                        print(f"⏳ Stalking panic (${target_scalp:.2f}) | Current bid: ${current_bid} | Max Bounce: ${max_bid_seen:.2f}")
                    elif has_sold and int(seconds_left * 10) % 50 == 0:
                        print(f"📡 Recording silent data... | Ceiling detected so far: ${max_bid_seen:.2f} | {int(seconds_left)}s left")
                
                time.sleep(0.1)

        except:
            time.sleep(1)

print("\n" + "="*30)
print(f"📊 FULL EXIT EXPERIMENT FINAL RESULTS")
print(f"Balance: ${simulated_balance:.2f} USDC | Wins: {wins} | Losses: {losses}")
print("="*30)
