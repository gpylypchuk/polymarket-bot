import pandas as pd
import matplotlib.pyplot as plt
import os

csv_filename = "paper_trading_log.csv"

def plot_equity_curve():
    if not os.path.exists(csv_filename):
        print(f"❌ No se encontró el archivo {csv_filename}. Dejá correr el bot primero.")
        return

    # 1. Leer los datos
    df = pd.read_csv(csv_filename)
    
    if df.empty:
        print("⚠️ El CSV está vacío. Aún no hay trades registrados.")
        return

    # 2. Calcular el Profit Acumulado
    df['Cumulative_Profit'] = df['Profit_USDC'].cumsum()

    # 3. Configurar el gráfico
    plt.figure(figsize=(12, 6))
    
    # Dibujar la línea principal
    plt.plot(df.index + 1, df['Cumulative_Profit'], label='Balance Acumulado', color='#2ca02c', linewidth=2)

    # 4. Marcar los trades ganados y perdidos con colores
    ganados = df[df['Status'] == 'SUCCESS']
    perdidos = df[df['Status'] == 'TIMEOUT']

    plt.scatter(ganados.index + 1, ganados['Cumulative_Profit'], color='green', label='Trade Exitoso', zorder=5, s=50)
    plt.scatter(perdidos.index + 1, perdidos['Cumulative_Profit'], color='red', label='Timeout / Pérdida', zorder=5, s=50)

    # 5. Estética del gráfico
    plt.title('Rendimiento de la Estrategia: Paper Bot', fontsize=14, fontweight='bold')
    plt.xlabel('Número de Trade', fontsize=12)
    plt.ylabel('Profit Acumulado (USDC)', fontsize=12)
    plt.axhline(0, color='black', linestyle='--', linewidth=1) # Línea de base cero
    plt.grid(True, linestyle=':', alpha=0.7)
    plt.legend()
    
    # Ajustar etiquetas del eje X a números enteros
    plt.xticks(df.index + 1)

    # 6. Mostrar métricas clave en consola
    print("\n📊 --- RESUMEN DE RENDIMIENTO ---")
    print(f"Total Trades: {len(df)}")
    print(f"Win Rate: {(len(ganados) / len(df)) * 100:.1f}%")
    print(f"Profit Total: ${df['Profit_USDC'].sum():.2f} USDC")
    print(f"Mejor Trade: +${df['Profit_USDC'].max():.2f} USDC")
    print(f"Peor Trade: ${df['Profit_USDC'].min():.2f} USDC")
    print("---------------------------------\n")

    # Mostrar gráfico
    plt.show()

if __name__ == "__main__":
    plot_equity_curve()