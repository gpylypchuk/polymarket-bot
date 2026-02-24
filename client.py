import os, json, time, requests, threading, websocket
from py_clob_client.clob_types import MarketOrderArgs, OrderType, OrderArgs
from py_clob_client.client import ClobClient
from py_clob_client.order_builder.constants import BUY, SELL
from datetime import datetime, timezone
from dotenv import load_dotenv
from collections import deque

load_dotenv()

def best_prices(book):
    best_bid = float(book.bids[-1].price) if book.bids else None
    best_ask = float(book.asks[0].price) if book.asks else None
    last_trade = float(book.last_trade_price)
    return best_bid, best_ask, last_trade

# 1. SENSOR CON BUFFER DE PERSISTENCIA
price_buffer = deque(maxlen=3) # Guardamos solo las últimas 3 actualizaciones
btc_price_live = 0.0

def on_message(ws, message):
    global btc_price_live
    data = json.loads(message)
    price = float(data['c'])
    btc_price_live = price
    price_buffer.append(price)

def run_binance_ws():
    ws = websocket.WebSocketApp("wss://stream.binance.com:9443/ws/btcusdt@ticker", on_message=on_message)
    ws.run_forever()

threading.Thread(target=run_binance_ws, daemon=True).start()

host = "https://clob.polymarket.com"
chain_id = 137  # Polygon mainnet
private_key = os.getenv("PRIVATE_KEY")

# Derive API credentials
temp_client = ClobClient(host, key=private_key, chain_id=chain_id)
api_creds = temp_client.create_or_derive_api_creds()

# Initialize trading client
client = ClobClient(
    host,
    key=private_key,
    chain_id=chain_id,
    creds=api_creds,
    signature_type=0,
    funder=os.getenv("FUNDER_ADDRESS")
)

# Verificar saldo y allowance (opcional, para debug)
# print(client.get_balance_allowance(
#     BalanceAllowanceParams(
#         asset_type="COLLATERAL",
#         token_id="",
#         signature_type=0
#     )
# ))

# Configuramos la cantidad de ejecuciones de prueba
MAX_TESTS = 5
test_count = 0

print(f"🤖 Bot iniciado. Modo prueba: {MAX_TESTS} ciclos.")

while test_count < MAX_TESTS:
    # 1. DETECTAR EL SLOT ACTUAL
    now_ts = int(time.time())
    start_slot = (now_ts // 300) * 300
    slug = f"btc-updown-5m-{start_slot}"
    
    # Esperamos a tener datos en el buffer
    while btc_price_live == 0 or len(price_buffer) < 3:
        time.sleep(1)
    
    p_strike = btc_price_live
    print(f"📍 Strike fijado: ${p_strike} para el slot {start_slot}")

    # 2. OBTENER DATA DEL MERCADO
    try:
        r = requests.get(f"https://gamma-api.polymarket.com/events?slug={slug}")
        event_data = r.json()
        if not event_data:
            time.sleep(10); continue
        
        market = event_data[0]["markets"][0]
        clob_ids = json.loads(market["clobTokenIds"]) # [UP_ID, DOWN_ID]
        outcomes = json.loads(market["outcomes"])     # ["Up", "Down"]
        market_id = market["id"]
    except:
        time.sleep(5); continue

    # 3. BUCLE DE MONITOREO
    market_active = True

    while market_active:
        try:
            # 2. ACTUALIZAR TIEMPO
            market_data = client.get_market(market_id)
            seconds_left = (datetime.fromisoformat(market_data.get("endDate").replace("Z", "+00:00")) - datetime.now(timezone.utc)).total_seconds()

            if seconds_left <= 0:
                print("🏁 El mercado actual cerró. Buscando el próximo slot...")
                time.sleep(5)
                break # Buscamos el nuevo start_slot

            # 3. FILTRO DE TIEMPO
            if 0 < seconds_left <= 70:
                # --- FILTRO DE PERSISTENCIA (3 muestras > $50) ---
                # Comprobamos si las 3 últimas capturas confirman la tendencia
                all_up = all((p - p_strike) > 50 for p in price_buffer)
                all_down = all((p_strike - p) > 50 for p in price_buffer)
                # 4. BUCLE DE TRADING
                for outcome, token_id in zip(outcomes, clob_ids):
                    # FILTRO DIRECCIONAL: Solo miramos el token que coincide con la tendencia de BTC
                    trend_confirmed = (outcome == "Up" and all_up) or (outcome == "Down" and all_down)

                    if trend_confirmed:
                        book = client.get_order_book(token_id)
                        best_bid, best_ask, last_trade = best_prices(book)

                        if best_bid and 0.92 <= best_bid <= 0.98:
                            print(f"🚀 SEÑAL CONFIRMADA: BTC movió >$50. Disparando {outcome}...")
                            try:
                                buy_args = MarketOrderArgs(
                                    token_id=token_id,
                                    amount=4.9,         
                                    side=BUY,
                                    price=best_ask + 0.01 
                                )
                                buy_res = client.post_order(client.create_market_order(buy_args), OrderType.FOK)
                                order_id = buy_res.get("orderID")
                                print(f"🔥 DISPARANDO: {outcome} a ${best_bid}")

                                if order_id:
                                    time.sleep(0.7) # Sincronización
                                    order_info = client.get_order(order_id)
                                    
                                    shares_compradas = float(order_info.get("filled_size", 0))
                                    p_entrada = float(order_info.get("price", 0))

                                    if shares_compradas >= 5.0:
                                        print(f"✅ Compra ejecutada. Llenado: {shares_compradas} a ${p_entrada}")

                                        # LÓGICA DE VENTA
                                        target_price = round(p_entrada * 1.03, 2)
                                        if target_price > 0.98: target_price = 0.99
                                        if target_price <= p_entrada: target_price = p_entrada + 0.01

                                        sell_res = client.post_order(client.create_order(OrderArgs(
                                            token_id=token_id,
                                            price=target_price,
                                            size=shares_compradas,
                                            side=SELL
                                        )))
                                        
                                        if sell_res.get("success"):
                                            test_count += 1
                                            print(f"✅ PRUEBA {test_count}/5 EXITOSA.")
                                            time.sleep(seconds_left + 5)
                                            market_active = False
                                            break
                                else:
                                    print(f"❌ Orden no ejecutada (FOK): {buy_res.get('errorMsg')}")
                            except Exception as e:
                                print(f"⚠️ Error en orden: {e}")
                time.sleep(0.5) # Frecuencia de escaneo en zona hot
            else:
                # Ahorro de API fuera de la zona crítica
                print(f"⏳ {int(seconds_left)}s para el cierre. BTC: ${btc_price_live} | Diff: ${abs(btc_price_live - p_strike):.2f}")
                time.sleep(10)
        except Exception as e:
                print(f"⚠️ Error en monitoreo: {e}"); time.sleep(2)
print("🏁 Fin de las 5 pruebas. ¡Revisá tus profits en la web!")