import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import os

fig, ax = plt.subplots(figsize=(10, 5))
fig.canvas.manager.set_window_title('📊 Monitor de Rendimiento')

def actualizar_grafico(i):
    archivo_csv = "paper_trading_log.csv"
    
    if not os.path.exists(archivo_csv):
        return
        
    try:
        # Leemos el CSV
        df = pd.read_csv(archivo_csv)
        
        if len(df) == 0:
            return
            
        df['Balance_Acumulado'] = df['Profit_USDC'].cumsum()
        
        ax.clear()
        
        # Linea de rendimiento
        ax.plot(df.index + 1, df['Balance_Acumulado'], marker='o', linestyle='-', color='#00d1b2', linewidth=2)
        
        if df['Balance_Acumulado'].iloc[-1] >= 0:
            ax.fill_between(df.index + 1, df['Balance_Acumulado'], 0, alpha=0.2, color='green')
        else:
            ax.fill_between(df.index + 1, df['Balance_Acumulado'], 0, alpha=0.2, color='red')

        # Linea de Cero (Breakeven)
        ax.axhline(0, color='gray', linestyle='--', linewidth=1)
        
        ax.set_title(f"Balance Simulado en Tiempo Real | Trades: {len(df)} | P&L: ${df['Balance_Acumulado'].iloc[-1]:.2f} USDC", fontsize=14, fontweight='bold')
        ax.set_xlabel("Número de Operación (Trade)", fontsize=10)
        ax.set_ylabel("Ganancia Acumulada (USDC)", fontsize=10)
        ax.grid(True, linestyle=':', alpha=0.7)
        
        ax.xaxis.set_major_locator(plt.MaxNLocator(integer=True))
        
    except Exception as e:
        # Si el bot justo está escribiendo el CSV, ignoramos el error y esperamos al próximo ciclo
        pass

# Actualizamos la funcion cada 3 segundos
ani = FuncAnimation(fig, actualizar_grafico, interval=3000, cache_frame_data=False)

print("📈 Abriendo monitor en tiempo real... (Dejá esta ventana abierta)")
plt.tight_layout()
plt.show()