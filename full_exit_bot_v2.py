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
trades_ganados = 0
trades_perdidos = 0

csv_filename = os.path.join("logs", "full_exit_experiment_log_v2.csv")
os.makedirs("logs", exist_ok=True)

if not os.path.exists(csv_filename):
    with open(csv_filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Timestamp", "Slot", "Outcome", "Shares", "Entry_Price", "Target_Price", "Exit_Price", "Max_Bid_Seen", "Profit_USDC", "Status"])

def log_trade(slot, outcome, shares, p_in, target, p_out, max_bid, profit, status):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(csv_filename, mode='a', newline='') as f:
        csv.writer(f).writerow([timestamp, slot, outcome, round(shares, 2), p_in, target, p_out, max_bid, round(profit, 4), status])

print("=======================================")
print(f"🧪 PAPER TRADING | BOT 3: FULL EXIT SCALPER")
print(f"🎯 Rango de Entrada: 0.01 - 0.02")
print("⚡ Salida Total: TP 0.25 (Sin Free Roll)")
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

    while market_active:
        try:
            seconds_left = (end_date - datetime.now(timezone.utc)).total_seconds()

            if seconds_left <= 0:
                if trade_open:
                    win = (token_outcome == "Up" and btc_price_live >= p_strike) or \
                          (token_outcome == "Down" and btc_price_live < p_strike)
                    
                    p_final = 1.00 if win else 0.00
                    profit = (p_final * shares_sim) - costo_sim
                    simulated_balance += profit
                    if win: trades_ganados += 1
                    else: trades_perdidos += 1
                    
                    status = "WIN_ORACLE" if win else "LOSS_ORACLE"
                    print(f"{'🏆' if win else '💀'} RESULTADO ORÁCULO: {status} | Profit: ${profit:.2f}")
                    log_trade(start_slot, token_outcome, shares_sim, p_entrada_sim, target_scalp, p_final, max_bid_seen, profit, status)
                    test_count += 1
                market_active = False; break

            if not trade_open:
                hot_zone_extrema = (0 < seconds_left <= 45) and all(abs(p - p_strike) > 40 for p in price_buffer)
                hot_zone_normal = (0 < seconds_left <= 20) and all(abs(p - p_strike) > 25 for p in price_buffer)

                if hot_zone_extrema or hot_zone_normal:
                    trend_up = all((p - p_strike) > 0 for p in price_buffer)
                    target_outcome = "Down" if trend_up else "Up" 
                    target_token_id = clob_ids[1] if trend_up else clob_ids[0]

                    _, best_ask = get_raw_best_prices(target_token_id)

                    if best_ask:
                        if int(seconds_left * 10) % 20 == 0:
                            diff = btc_price_live - p_strike
                            print(f"🔍 [CISNE NEGRO] BTC Diff: ${diff:.2f} | Evaluando la contra ({target_outcome}) a ${best_ask:.2f}")

                        if 0.01 <= best_ask <= 0.02:
                            p_entrada_sim = best_ask
                            shares_sim = 20.0  
                            costo_sim = shares_sim * p_entrada_sim
                            
                            target_scalp = 0.25
                            max_bid_seen = 0.0 

                            print(f"\n🚀 [FULL ENTRY] Comprando {shares_sim} shares de {target_outcome} a ${p_entrada_sim:.2f}")
                            print(f"🎯 TARGET ÚNICO: ${target_scalp:.2f} (Venta Total)")
                            
                            trade_open = True
                            token_activo = target_token_id 
                            token_outcome = target_outcome
                            
                        elif best_ask > 0.02:
                            if int(seconds_left * 10) % 20 == 0: print(f"⚠️ [STALKING] Contra muy cara (${best_ask:.2f}). Esperando a 0.02...")
                
                elif int(seconds_left) % 10 == 0:
                    print(f"⏳ {int(seconds_left)}s para cierre. BTC: ${btc_price_live:.2f} | Diff: ${abs(btc_price_live - p_strike):.2f}")
                
                time.sleep(0.2) 

            elif trade_open:
                current_bid, _ = get_raw_best_prices(token_activo)
                
                if current_bid:
                    if current_bid > max_bid_seen:
                        max_bid_seen = current_bid
                
                # VENTA TOTAL SI TOCA 0.25
                if current_bid and current_bid >= target_scalp:
                    profit_total = (current_bid * shares_sim) - costo_sim
                    simulated_balance += profit_total
                    trades_ganados += 1 
                    
                    print(f"\n💸 ¡PANIC SCALP EXITOSO! Vendiendo TODAS LAS {shares_sim} shares a ${current_bid:.2f} | Profit Limpio: +${profit_total:.2f}")
                    log_trade(start_slot, token_outcome, shares_sim, p_entrada_sim, target_scalp, current_bid, max_bid_seen, profit_total, "FULL_PROFIT")
                    test_count += 1
                    
                    time.sleep(seconds_left + 5) 
                    market_active = False; break
                    
                else:
                    if int(seconds_left * 10) % 20 == 0:
                        print(f"⏳ Acechando pánico (${target_scalp:.2f}) | Bid actual: ${current_bid} | Max Rebote Visto: ${max_bid_seen:.2f}")
                
                time.sleep(0.2)
        except:
            time.sleep(1)

print("\n" + "="*30)
print(f"📊 RESULTADOS FINALES EXPERIMENTO FULL EXIT")
print(f"Balance: ${simulated_balance:.2f} USDC | Ganados: {trades_ganados} | Perdidos: {trades_perdidos}")
print("="*30)