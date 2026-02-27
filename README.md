# 🎯 Polymarket BTC-5m Scalper

Este es un bot diseñado para capturar movimientos de momentum extremo en los mercados de **BTC Up/Down de 5 minutos** en Polymarket. Utiliza un sensor de baja latencia vía WebSockets para detectar la tendencia final antes del cierre del mercado.

⚠️ **ESTADO DEL PROYECTO: DEPRECADO (BETA-TESTING CERRADO)**
*A pesar de poseer un Win Rate superior al 97.2%, el modelo fue descartado para operar en producción debido a una Esperanza Matemática (Kelly) fuertemente negativa impuesta por la microestructura del Order Book de Polymarket.*

---

## 💸 La Estrategia Original: Momentum & Persistencia

La hipótesis inicial buscaba explotar la capitulación de precio en los últimos segundos de cada intervalo de 5 minutos, asumiendo un riesgo direccional "seguro".

### 1. Referencia de Strike y Zona de Disparo
Al inicio de cada bloque, el bot sincroniza el **Strike Price** ($P_{strike}$) desde el ticker de Binance. Monitorea activamente el Order Book únicamente en los últimos **70 segundos**, evitando el ruido estructural y enfocándose en la resolución final.

### 2. Filtro de Señal (Persistence Check)
Para filtrar falsos movimientos, el bot exige una confirmación brutal de tendencia:
* **Diferencial**: $\Delta = |P_{actual} - P_{strike}|$
* **Persistencia**: El diferencial debe ser $> 50$ USD durante **3 actualizaciones seguidas** del WebSocket de Binance.
* **Ejecución**: Se dispara la compra "segura" en el rango de **0.96 a 0.98** buscando vender a 0.99.

---

## 🩸 La Autopsia: Por qué NO es rentable

Tras simular 111 operaciones reales en el Order Book de Polymarket, los datos arrojaron un resultado contraintuitivo pero irrefutable.



La estrategia sufre del síndrome de *"juntar monedas adelante de una aplanadora"*. Al comprar opciones "seguras" a 0.98, el bot gana apenas $0.01 o $0.02 por trade exitoso, pero expone un capital masivo si el mercado revierte en el último segundo.

### El Criterio de Kelly Negativo

Analizando la muestra de 111 trades, obtuvimos los siguientes promedios:
* **Aciertos:** 108 trades (Ganancia promedio: $0.079)
* **Fallos:** 3 trades (Pérdida promedio: $3.75 debido al slippage extremo por falta de liquidez).
* **Win Rate ($p$):** 97.29%
* **Loss Rate ($q$):** 2.71%
* **Ratio de Pago ($b$):** 0.021 (Ganancia promedio / Riesgo máximo).



Aplicando la fórmula de dimensionamiento óptimo de Kelly:

$$f^* = p - \frac{q}{b}$$

$$f^* = 0.973 - \frac{0.027}{0.021}$$

$$f^* = -0.312$$

**Resultado: Kelly de -31.2%.** Matemáticamente, la fórmula exige no invertir capital en este modelo.

---

## 🛠️ Stack Tecnológico

* **Lenguaje**: Python 3.10+
* **Data Feed**: Binance WebSocket API (Real-time ticker).
* **Ejecución**: Requests Session de baja latencia consultando el Polymarket CLOB.
* **Filtros**: Buffer circular (`deque`) para procesamiento de señales y mitigación de ruido.

---

## 🚀 Uso (Para fines de estudio)
1. Configurar el archivo `.env` con `PRIVATE_KEY` y `FUNDER_ADDRESS`.
2. Lanzar el bot:
   ```bash
   python paper_bot.py
