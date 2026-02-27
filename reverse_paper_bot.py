import os, json, time, requests, threading, websocket, csv
from datetime import datetime, timezone
from dotenv import load_dotenv
from collections import deque

load_dotenv()

# --- 1. SENSOR BURSÁTIL (Binance WS) ---
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

# --- 2. MOTOR HTTP DE ALTA VELOCIDAD ---
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

# --- 3. MÉTRICAS Y LOG DE EXPERIMENTO ---
MAX_TESTS = 50
test_count = 0
simulated_balance = 0.0
trades_ganados = 0
trades_perdidos = 0

csv_filename = os.path.join("logs", "reversion_experiment_log.csv")
if not os.path.exists(csv_filename):
    with open(csv_filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Timestamp", "Slot", "Type", "Entry", "Exit_Price", "Profit_USDC", "Status"])

def log_trade(slot, outcome, p_in, p_out, profit, status):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(csv_filename, mode='a', newline='') as f:
        csv.writer(f).writerow([timestamp, slot, outcome, p_in, p_out, round(profit, 4), status])

print("=======================================")
print(f"🧪 PAPER TRADING V8 | {MAX_TESTS} CICLOS")
print("🎯 Objetivo: Compras a $0.05 (Lotería)")
print("⚡ Salida Dual: TP 0.20 o Expiración $1.00")
print("=======================================\n")

# --- 4. BUCLE PRINCIPAL ---
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
                    # RESOLUCIÓN POR ORÁCULO
                    win = (token_outcome == "Up" and btc_price_live >= p_strike) or \
                          (token_outcome == "Down" and btc_price_live < p_strike)
                    
                    p_final = 1.00 if win else 0.00
                    profit = (p_final * shares_sim) - costo_sim
                    simulated_balance += profit
                    if win: trades_ganados += 1
                    else: trades_perdidos += 1
                    
                    status = "WIN_ORACLE" if win else "LOSS_ORACLE"
                    print(f"{'🏆' if win else '💀'} RESULTADO: {status} | Profit: ${profit:.2f}")
                    log_trade(start_slot, token_outcome, p_entrada_sim, p_final, profit, status)
                    test_count += 1
                market_active = False; break

            if not trade_open:
                # Solo buscamos si el precio esta "cerca" pero el mercado cree que ya perdio
                if 0 < seconds_left <= 65:
                    trend_up = (btc_price_live > p_strike)
                    # Apostamos al que va PERDIENDO (buscando reversión)
                    target_outcome = "Down" if trend_up else "Up"
                    target_id = clob_ids[1] if trend_up else clob_ids[0]
                    
                    _, best_ask = get_raw_best_prices(target_id)
                    
                    if best_ask and 0.02 <= best_ask <= 0.08:
                        p_entrada_sim = best_ask
                        shares_sim = 20.0 # Más volumen para aprovechar el precio bajo
                        costo_sim = p_entrada_sim * shares_sim
                        token_activo = target_id
                        token_outcome = target_outcome
                        trade_open = True
                        print(f"🎟️ TICKET COMPRADO: {target_outcome} a ${best_ask}")
                
                elif int(seconds_left) % 15 == 0:
                    print(f"⏳ {int(seconds_left)}s | BTC: ${btc_price_live} | Dif: ${abs(btc_price_live-p_strike):.2f}")

            elif trade_open:
                # MONITOREO DE SALIDA RÁPIDA (Dual Exit)
                current_bid, _ = get_raw_best_prices(token_activo)
                
                if current_bid and current_bid >= 0.20:
                    profit = (current_bid * shares_sim) - costo_sim
                    simulated_balance += profit
                    trades_ganados += 1
                    print(f"⚡ SALIDA RÁPIDA (4x): Vendido a ${current_bid} | Profit: ${profit:.2f}")
                    log_trade(start_slot, token_outcome, p_entrada_sim, current_bid, profit, "FAST_EXIT")
                    trade_open = False
                    test_count += 1
                    market_active = False # Esperamos al siguiente slot

            time.sleep(0.2)
        except:
            time.sleep(1)

print("\n" + "="*30)
print(f"📊 RESULTADOS FINALES EXPERIMENTO")
print(f"Balance: ${simulated_balance:.2f} USDC | Ganados: {trades_ganados} | Perdidos: {trades_perdidos}")
print("="*30)