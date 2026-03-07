use std::collections::VecDeque;
use std::sync::Arc;
use std::time::{SystemTime, UNIX_EPOCH};
use tokio::sync::RwLock;
use tokio_tungstenite::{connect_async, tungstenite::protocol::Message};
use futures_util::StreamExt;
use serde::Deserialize;

#[derive(Deserialize)]
struct BinanceAggTrade {
    p: String, // Precio
    q: String, // Cantidad
    m: bool,   // Si es una venta (true) o compra (false)
}

struct MarketState {
    btc_price_live: f64,
    ofi_1s: f64,
    price_buffer: VecDeque<f64>,
    trade_window: VecDeque<(f64, f64)>, // (Timestamp_ms, Volumen)
}

impl MarketState {
    fn new() -> Self {
        Self {
            btc_price_live: 0.0,
            ofi_1s: 0.0,
            price_buffer: VecDeque::with_capacity(3),
            trade_window: VecDeque::new(),
        }
    }
}

#[tokio::main]
async fn main() {
    println!("=======================================");
    println!("🦀 RUST HFT ENGINE | HYBRID L2 RADAR V3");
    println!("⚡ Architecture: Tokio + Arc<RwLock>");
    println!("=======================================\n");

    let state = Arc::new(RwLock::new(MarketState::new()));
    let state_for_ws = state.clone();

    tokio::spawn(async move {
        let url = "wss://stream.binance.com:9443/ws/btcusdt@aggTrade";
        let (ws_stream, _) = connect_async(url).await.expect("Error conectando a Binance");
        println!("✅ [WS] Conectado a Binance AggTrade");

        let (_, mut read) = ws_stream.split();

        while let Some(msg) = read.next().await {
            if let Ok(Message::Text(text)) = msg {
                if let Ok(trade) = serde_json::from_str::<BinanceAggTrade>(&text) {
                    let price: f64 = trade.p.parse().unwrap_or(0.0);
                    let qty: f64 = trade.q.parse().unwrap_or(0.0);
                    let vol = if trade.m { -qty } else { qty };

                    let now = SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_secs_f64();

                    // Bloqueamos el estado solo un microsegundo para actualizar
                    let mut st = state_for_ws.write().await;
                    st.btc_price_live = price;
                    
                    if st.price_buffer.len() >= 3 {
                        st.price_buffer.pop_front();
                    }
                    st.price_buffer.push_back(price);

                    st.trade_window.push_back((now, vol));

                    // Limpieza de ventana de 1 segundo
                    while let Some(&(t, _)) = st.trade_window.front() {
                        if now - t > 1.0 {
                            st.trade_window.pop_front();
                        } else {
                            break;
                        }
                    }

                    // Calculo del OFI
                    st.ofi_1s = st.trade_window.iter().map(|&(_, v)| v).sum();
                }
            }
        }
    });

    // Equivalente a "while test_count < MAX_TESTS" de Python
    // Usamos reqwest Client (igual al requests.Session() de Python)
    let client = reqwest::Client::new();

    loop {
        // En Rust leemos la variable global pidiendo permiso al Lock
        let (current_price, current_ofi) = {
            let st = state.read().await;
            (st.btc_price_live, st.ofi_1s)
        };

        if current_price > 0.0 {
            // ACA VA LA LOGICA DE POLYMARKET:
            // 1. Calcular seconds_left
            // 2. Si seconds_left <= 15 -> Disparar client.get(clob_url)
            // 3. Analizar Muro < 4000
            
            // println!("BTC: ${:.2} | OFI: {:.2} BTC/s", current_price, current_ofi);
        }

        tokio::time::sleep(tokio::time::Duration::from_millis(100)).await;
    }
}