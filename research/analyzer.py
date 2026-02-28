import pandas as pd
import os

def analyze_performance():
    log_dir = "logs"
    files = {
        "Reversion Lab V2": "full_exit_experiment_log_v2.csv",
        "Reversion Lab V1": "full_exit_experiment_log_v1.csv"
    }

    print("📊 --- COMPARATIVA DE ESTRATEGIAS --- 📊\n")

    for name, filename in files.items():
        path = os.path.join(log_dir, filename)
        
        if not os.path.exists(path):
            print(f"⚠️ {name}: Sin datos todavía (esperando trades...).")
            continue

        try:
            df = pd.read_csv(path)
            
            # Limpieza básica por si hay filas vacías
            df = df.dropna(subset=['Profit_USDC'])
            
            total_profit = df['Profit_USDC'].sum()
            total_trades = len(df)
            win_rate = (len(df[df['Profit_USDC'] > 0]) / total_trades * 100) if total_trades > 0 else 0
            max_win = df['Profit_USDC'].max()
            max_loss = df['Profit_USDC'].min()

            print(f"🔹 ESTRATEGIA: {name}")
            print(f"   💰 Profit Total: ${total_profit:.2f} USDC")
            print(f"   📈 Win Rate:     {win_rate:.1f}%")
            print(f"   🔄 Total Trades: {total_trades}")
            print(f"   🚀 Mejor Trade:  +${max_win:.2f}")
            print(f"   📉 Peor Trade:   ${max_loss:.2f}")
            print("-" * 35)
        except Exception as e:
            print(f"❌ Error analizando {filename}: {e}")

if __name__ == "__main__":
    analyze_performance()