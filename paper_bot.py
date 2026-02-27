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

# --- 2. MOTOR HTTP DE ALTA VELOCIDAD (Bypass SDK) ---
fast_session = requests.Session()
fast_session.headers.update({'User-Agent': 'Mozilla/5.0'})

def get_raw_best_prices(token_id):
    """Consulta directa y A PRUEBA DE BALAS al CLOB de Polymarket"""
    try:
        res = fast_session.get(f"https://clob.polymarket.com/book?token_id={token_id}", timeout=2).json()
        
        if res.get('bids') and len(res['bids']) > 0:
            best_bid = max(float(b['price']) for b in res['bids'])
        else:
            best_bid = None
            
        if res.get('asks') and len(res['asks']) > 0:
            best_ask = min(float(a['price']) for a in res['asks'])
        else:
            best_ask = None
            
        return best_bid, best_ask
    except Exception:
        return None, None

# --- 3. MÉTRICAS Y LOG DE SIMULACIÓN ---
MAX_TESTS = 288
test_count = 0
simulated_balance = 0.0
trades_ganados = 0
trades_perdidos = 0

csv_filename = os.path.join("logs", "paper_trading_bot.csv")
if not os.path.exists(csv_filename):
    with open(csv_filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Timestamp", "Slot", "Outcome", "Shares", "Entry_Price", "Target_Price", "Exit_Price", "Profit_USDC", "Status"])

def log_trade(slot, outcome, shares, p_in, target, p_out, profit, status):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(csv_filename, mode='a', newline='') as f:
        csv.writer(f).writerow([timestamp, slot, outcome, round(shares, 2), p_in, target, p_out, round(profit, 4), status])

print("=======================================")
print(f"🧪 PAPER TRADING V8 - MODO BARREDORA | {MAX_TESTS} CICLOS")
print("⚡ Optimizaciones: Sesión Persistente HTTP + Direct JSON")
print("⚙️ Gatillos Anticipados: >$25 (70s) | >$15 (40s)")
print("🕵️‍♂️ Rango de entrada: $0.96 a $0.98")
print("=======================================\n")

# --- 4. BUCLE PRINCIPAL ---
while test_count < MAX_TESTS:
    now_ts = int(time.time())
    start_slot = (now_ts // 300) * 300
    slug = f"btc-updown-5m-{start_slot}"
    
    # SETUP DEL SLOT (REST Gamma API + Binance Klines)
    try:
        r = requests.get(f"https://gamma-api.polymarket.com/events?slug={slug}")
        event_data = r.json()
        if not event_data: 
            time.sleep(10); continue
        
        market = event_data[0]["markets"][0]
        clob_ids = json.loads(market["clobTokenIds"])
        outcomes = json.loads(market["outcomes"])
        end_date = datetime.fromisoformat(market.get("endDate").replace("Z", "+00:00"))

        # Strike Oficial (Binance Open Price)
        start_time_ms = int(datetime.fromisoformat(event_data[0].get("startTime", "").replace("Z", "+00:00")).timestamp() * 1000)
        k_res = requests.get(f"https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=5m&startTime={start_time_ms}&limit=1")
        k_data = k_res.json()
        
        if k_data and len(k_data) > 0:
            p_strike = float(k_data[0][1])
            print(f"\n📍 [SLOT {start_slot}] Strike Oficial: ${p_strike}")
        else:
            p_strike = btc_price_live 
    except Exception as e:
        print(f"⚠️ Error cargando slot: {e}")
        time.sleep(5); continue

    # Sincronización
    while btc_price_live == 0 or len(price_buffer) < 3: 
        time.sleep(1)

    market_active = True
    trade_open = False 

    # --- 5. BUCLE DE MONITOREO DE ALTA FRECUENCIA ---
    while market_active:
        try:
            seconds_left = (end_date - datetime.now(timezone.utc)).total_seconds()

            if seconds_left <= 0:
                print("\n🏁 Mercado cerrado.")
                if trade_open:
                    print("⚖️ Resolviendo mercado por expiración (Oráculo Simulado)...")
                    
                    # Determinamos si el trade fue exitoso basándonos en el precio final de BTC
                    if (token_outcome == "Up" and btc_price_live >= p_strike) or \
                       (token_outcome == "Down" and btc_price_live < p_strike):
                        
                        # ¡Ganamos! Cada acción ahora vale $1.00 USDC
                        ingreso_final = 1.00 * shares_sim
                        profit_neto = ingreso_final - costo_sim
                        simulated_balance += profit_neto
                        trades_ganados += 1
                        
                        print(f"🏆 ¡GANASTE POR EXPIRACIÓN! El mercado resolvió a favor de {token_outcome}.")
                        print(f"💰 Profit: +${profit_neto:.2f} USDC | Balance: ${simulated_balance:.2f} USDC")
                        
                        log_trade(start_slot, token_outcome, shares_sim, p_entrada_sim, target_sim, 1.00, profit_neto, "EXPIRATION_WIN")
                    
                    else:
                        # Perdimos. BTC se dio vuelta en el último segundo. El token vale $0.00.
                        simulated_balance -= costo_sim
                        trades_perdidos += 1
                        
                        print(f"💀 PERDISTE POR EXPIRACIÓN. BTC rebotó y cerró en contra.")
                        log_trade(start_slot, token_outcome, shares_sim, p_entrada_sim, target_sim, 0.00, -costo_sim, "EXPIRATION_LOSS")
                market_active = False; break

            # A. ESTADO: BUSCANDO ENTRADA
            if not trade_open:
                # Faltando 45s, exigimos $40 de diferencia (antes era $25 a los 70s)
                hot_zone_extrema = (0 < seconds_left <= 45) and all(abs(p - p_strike) > 40 for p in price_buffer)
                # Faltando 20s, exigimos $25 de diferencia (antes era $15 a los 40s)
                hot_zone_normal = (0 < seconds_left <= 20) and all(abs(p - p_strike) > 25 for p in price_buffer)

                if hot_zone_extrema or hot_zone_normal:
                    trend_up = all((p - p_strike) > 0 for p in price_buffer)
                    target_outcome = "Up" if trend_up else "Down"
                    target_token_id = clob_ids[0] if trend_up else clob_ids[1]

                    _, best_ask = get_raw_best_prices(target_token_id)

                    if best_ask:
                        if int(seconds_left * 10) % 20 == 0:
                            diff = btc_price_live - p_strike if trend_up else p_strike - btc_price_live
                            print(f"🔍 [RAYOS X] Evaluando {target_outcome} | Ask: ${best_ask:.2f} | Diff BTC: ${abs(diff):.2f}")

                        if 0.96 <= best_ask <= 0.98: 
                            p_entrada_sim = best_ask
                            shares_sim = 5.0
                            costo_sim = shares_sim * p_entrada_sim
                            
                            target_sim = round(p_entrada_sim * 1.02, 2)
                            if target_sim > 0.99: target_sim = 0.99
                            if target_sim <= p_entrada_sim: target_sim = p_entrada_sim + 0.01 
                            
                            # 🛡️ NUEVO: Definimos el Stop Loss
                            stop_loss_sim = 0.30

                            print(f"\n🚀 [SEÑAL VÁLIDA] Disparando {target_outcome} a ${p_entrada_sim:.2f}")
                            print(f"🎯 TAKE PROFIT: ${target_sim:.2f}")
                            print(f"🛑 STOP LOSS: ${stop_loss_sim:.2f}")
                            
                            trade_open = True
                            token_activo = target_token_id 
                            token_outcome = target_outcome
                            
                        elif best_ask > 0.98:
                            if int(seconds_left * 10) % 20 == 0: print(f"⚠️ [STALKING] Ask muy caro (${best_ask:.2f}).")
                        elif best_ask < 0.96:
                            if int(seconds_left * 10) % 20 == 0: print(f"⚠️ [IGNORANDO] Ask muy barato (${best_ask:.2f}).")
                
                elif int(seconds_left) % 10 == 0:
                    print(f"⏳ {int(seconds_left)}s para cierre. BTC: ${btc_price_live:.2f} | Diff: ${abs(btc_price_live - p_strike):.2f}")
                
                time.sleep(0.1) 

            # B. ESTADO: MONITOREANDO SALIDA (Con Stop Loss)
            elif trade_open:
                current_bid, _ = get_raw_best_prices(token_activo)
                
                # 1. Escenario Ganador: Alcanzamos el Take Profit
                if current_bid and current_bid >= target_sim:
                    profit_neto = (current_bid * shares_sim) - costo_sim
                    simulated_balance += profit_neto
                    trades_ganados += 1
                    
                    print(f"\n✅ VENTA EXITOSA a ${current_bid:.2f}! Profit: +${profit_neto:.2f} USDC")
                    log_trade(start_slot, token_outcome, shares_sim, p_entrada_sim, target_sim, current_bid, profit_neto, "SUCCESS")
                    
                    test_count += 1
                    time.sleep(seconds_left + 5) 
                    market_active = False; break
                    
                # 2. 🛡️ NUEVO: Escenario Perdedor (Activación del Stop Loss)
                elif current_bid and current_bid <= stop_loss_sim:
                    profit_neto = (current_bid * shares_sim) - costo_sim
                    simulated_balance += profit_neto  # Sumamos un número negativo (pérdida)
                    trades_perdidos += 1
                    
                    print(f"\n🛑 ¡STOP LOSS ACTIVADO! El mercado colapsó.")
                    print(f"🩸 Venta de emergencia a ${current_bid:.2f} | Pérdida controlada: ${profit_neto:.2f} USDC")
                    log_trade(start_slot, token_outcome, shares_sim, p_entrada_sim, target_sim, current_bid, profit_neto, "STOP_LOSS")
                    
                    test_count += 1
                    time.sleep(seconds_left + 5) 
                    market_active = False; break
                    
                # 3. Escenario de Espera
                else:
                    if int(seconds_left * 10) % 20 == 0:
                        print(f"⏳ Monitoreando... Bid actual: ${current_bid} (Target: ${target_sim:.2f} | Stop: ${stop_loss_sim:.2f})")

                # Frecuencia 10Hz
                time.sleep(0.1)

        except Exception as e:
                print(f"⚠️ Error de red en zona activa: {e}")
                time.sleep(1)

print("\n=======================================")
print("📊 RESUMEN FINAL DEL PAPER TRADING V8")
print(f"Trades Ganados: {trades_ganados}")
print(f"Trades Perdidos/Timeout: {trades_perdidos}")
print(f"Balance Final: ${simulated_balance:.2f} USDC")
print("=======================================")