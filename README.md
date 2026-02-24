# 🎯 Polymarket BTC-5m Scalper

Este bot es un sistema de ejecución automatizada para capturar movimientos de momentum en los mercados de **BTC Up/Down de 5 minutos** en Polymarket. Utiliza un sensor de baja latencia vía WebSockets para detectar la tendencia final antes del cierre del mercado.

## 💸 Estrategia: Momentum & Persistencia

La estrategia busca explotar la capitulación de precio en los últimos segundos de cada intervalo de 5 minutos.

- Fuente de estrategia: me la inventé.

### 1. Referencia de Strike
Al inicio de cada bloque de 5 minutos, el bot sincroniza el **Strike Price** ($P_{strike}$) desde el ticker de Binance. Este valor sirve como línea base para medir el desplazamiento del precio.

### 2. Filtro de Tiempo (Zona de Disparo)
El bot monitorea activamente el Order Book únicamente en los últimos **70 segundos**. Esto evita el "ruido" de mitad de bloque y se enfoca en la resolución final del precio.

### 3. Filtro de Señal (Persistence Check)
Para filtrar falsos movimientos, el bot exige una confirmación de tendencia:
* **Diferencial**: $\Delta = |P_{actual} - P_{strike}|$
* **Persistencia**: El diferencial debe ser $> 50$ USD durante **3 actualizaciones seguidas** del WebSocket.
* **Direccionalidad**: El bot solo habilita la compra del token que coincide con la tendencia de BTC (Up si sube, Down si baja).



### 4. Gestión de Ejecución y Salida
* **Entrada**: Orden Market (FOK) si el `best_bid` está entre **0.92 y 0.98**.
* **Salida**: Orden Limit Sell con un objetivo de **+3%** de profit neto.
* **Prioridad**: Venta máxima en **0.99** para garantizar posición en el libro de órdenes frente a otros vendedores.



---

## 🛠️ Stack Tecnológico

* **Lenguaje**: Python 3.10+
* **Data Feed**: Binance WebSocket API (Real-time ticker).
* **Ejecución**: Polymarket CLOB SDK (Polygon Network).
* **Filtros**: Buffer circular (`deque`) para procesamiento de señales.

---

## 🚀 Uso
1. Configurar el archivo `.env` con `PRIVATE_KEY` y `FUNDER_ADDRESS`.
2. Lanzar el bot:
   ```bash
   python main.py

---

**Beta-Test**: Configurado para realizar 5 ciclos de prueba exitosos y detenerse para análisis de performance.
EOF