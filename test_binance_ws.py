import websocket
import json
import datetime

def on_message(ws, message):
    # 1. Recibimos el mensaje (un string JSON)
    data = json.loads(message)
    
    # 2. Extraemos los campos que nos interesan
    # 's' = Symbol (BTCUSDT)
    # 'c' = Current Price (Precio actual)
    # 'E' = Event Time (Timestamp del servidor)
    symbol = data['s']
    price = data['c']
    
    # 3. Formateamos la hora actual para el log
    timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
    
    # Imprimimos en consola
    print(f"[{timestamp}] {symbol} Live Price: ${price}")

def on_error(ws, error):
    print(f"❌ Error: {error}")

def on_close(ws, close_status_code, close_msg):
    print("🔌 Conexión cerrada")

def on_open(ws):
    print("✅ Conexión establecida con el WebSocket de Binance")
    print("Esperando datos... (Presioná Ctrl+C para salir)\n")

if __name__ == "__main__":
    # La URL del stream @ticker para BTCUSDT
    # Este stream nos manda actualizaciones cada 1000ms o ante cada cambio
    socket = "wss://stream.binance.com:9443/ws/btcusdt@ticker"
    
    ws = websocket.WebSocketApp(
        socket,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )

    # Iniciamos el loop infinito
    ws.run_forever()