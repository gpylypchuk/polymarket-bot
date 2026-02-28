import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import os

plt.style.use('dark_background')

fig, ax = plt.subplots(figsize=(12, 6))
fig.canvas.manager.set_window_title('📊 Monitor de Rendimiento Cuantitativo')

COLOR_LINEA = '#00e5ff'     # Cyan Neón
COLOR_POSITIVO = '#00e676'  # Verde Neón
COLOR_NEGATIVO = '#ff1744'  # Rojo Neón
COLOR_FONDO = '#0d1117'     # Fondo exacto de GitHub Dark Mode

fig.patch.set_facecolor(COLOR_FONDO)
ax.set_facecolor(COLOR_FONDO)

def actualizar_grafico(i):
    archivo_csv = os.path.join("logs", "paper_trading_log.csv") # Ojo: Asegurate de que este sea el nombre correcto
    
    if not os.path.exists(archivo_csv):
        return
        
    try:
        df = pd.read_csv(archivo_csv)
        
        if len(df) == 0:
            return
            
        df['Balance_Acumulado'] = df['Profit_USDC'].cumsum()
        x = df.index + 1
        y = df['Balance_Acumulado']
        
        ax.clear()
        
        ax.plot(x, y, color=COLOR_LINEA, linewidth=2.5, alpha=0.9, zorder=3)
        
        ax.fill_between(x, y, 0, where=(y >= 0), alpha=0.15, color=COLOR_POSITIVO, interpolate=True, zorder=1)
        ax.fill_between(x, y, 0, where=(y < 0), alpha=0.15, color=COLOR_NEGATIVO, interpolate=True, zorder=1)

        colores_puntos = [COLOR_POSITIVO if p > 0 else COLOR_NEGATIVO for p in df['Profit_USDC']]
        ax.scatter(x, y, color=colores_puntos, s=40, zorder=4, edgecolors=COLOR_FONDO, linewidth=0.8)

        # Línea de Cero (Breakeven)
        ax.axhline(0, color='white', linestyle='--', linewidth=1.5, alpha=0.4, zorder=2)
        
        balance_final = y.iloc[-1]
        signo = "+" if balance_final > 0 else ""
        
        ax.set_title(f"Equity Curve | Trades: {len(df)} | P&L Neto: {signo}{balance_final:.2f} USDC", 
                     fontsize=15, fontweight='bold', color='white', pad=15)
        ax.set_xlabel("Número de Operación", fontsize=11, color='lightgray', fontweight='bold')
        ax.set_ylabel("Ganancia Acumulada (USDC)", fontsize=11, color='lightgray', fontweight='bold')
        
        ax.grid(True, linestyle='--', alpha=0.15, color='white')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#444C56')
        ax.spines['bottom'].set_color('#444C56')
        ax.tick_params(colors='lightgray')
        
        ax.xaxis.set_major_locator(plt.MaxNLocator(integer=True))
        
        fig.tight_layout()
        
    except Exception as e:
        pass

ani = FuncAnimation(fig, actualizar_grafico, interval=3000, cache_frame_data=False)

print("📈 Abriendo monitor HFT estilo Dark Mode... (Capturá pantalla para GitHub)")
plt.show()