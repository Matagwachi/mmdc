import os
import sys
import datetime
import requests
import pandas as pd
import yfinance as yf

# Configuration des actifs demandés avec leurs tickers Yahoo Finance
ASSETS = {
    "EUR/USD": {"ticker": "EURUSD=X", "name": "EUR/USD", "format": "{:.4f}", "unit": ""},
    "Or": {"ticker": "GC=F", "name": "Or", "format": "{:,.2f}", "unit": " $"},
    "Brent": {"ticker": "BZ=F", "name": "Brent", "format": "{:,.2f}", "unit": " $"},
    "S&P 500": {"ticker": "^GSPC", "name": "S&P 500", "format": "{:,.2f}", "unit": " pts"}
}

def fetch_asset_data(ticker_symbol):
    """
    Récupère les données historiques via yfinance pour s'assurer d'obtenir
    les deux dernières clôtures valides (gère automatiquement les week-ends et jours fériés).
    """
    try:
        ticker = yf.Ticker(ticker_symbol)
        # On télécharge 5 jours glissants pour être sûr d'avoir les 2 dernières séances valides
        df = ticker.history(period="5d")
        
        if df is None or len(df) < 2:
            print(f"⚠️ Attention : données insuffisantes pour {ticker_symbol}")
            return None, None
        
        current_close = float(df['Close'].iloc[-1])
        previous_close = float(df['Close'].iloc[-2])
        return current_close, previous_close
    except Exception as e:
        print(f"❌ Erreur lors de la récupération de {ticker_symbol}: {e}")
        return None, None

def main():
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        print("❌ Erreur critique : La variable d'environnement DISCORD_WEBHOOK_URL est manquante.")
        sys.exit(1)

    today_str = datetime.datetime.now().strftime("%d/%m/%Y")
    report_lines = [f"📊 **Marchés — {today_str} — 07:00**"]
    
    up_count = 0
    down_count = 0
    stable_count = 0

    for key, config in ASSETS.items():
        current, previous = fetch_asset_data(config["ticker"])
        
        if current is None or previous is None:
            print(f"❌ Impossible de récupérer l'actif {key}. Arrêt du script.")
            sys.exit(1)
            
        variation = ((current - previous) / previous) * 100
        
        if variation > 0.005:
            emoji = "🟢"
            up_count += 1
            var_str = f"+{variation:.2f}%"
        elif variation < -0.005:
            emoji = "🔴"
            down_count += 1
            var_str = f"{variation:.2f}%"
        else:
            emoji = "⚪"
            stable_count += 1
            var_str = "0.00%"

        # Formatage de la valeur selon la configuration
        formatted_val = config["format"].format(current).replace(",", " ")
        line = f"💶 {config['name']} : {formatted_val}{config['unit']} ({var_str}) {emoji}"
        
        # Ajustement des émojis initiaux selon l'actif
        if key == "Or":
            line = line.replace("💶", "🥇")
        elif key == "Brent":
            line = line.replace("💶", "🛢️")
        elif key == "S&P 500":
            line = line.replace("💶", "📈")
            
        report_lines.append(line)

    # Construction du bilan
    summary_parts = []
    if up_count > 0:
        summary_parts.append(f"{up_count} en hausse")
    if down_count > 0:
        summary_parts.append(f"{down_count} en baisse")
    if stable_count > 0:
        summary_parts.append(f"{stable_count} stricts / stables")
        
    summary_str = ", ".join(summary_parts) if summary_parts else "aucun mouvement"
    report_lines.append(f"**Bilan :** {summary_str}.")

    final_message = "\n".join(report_lines)

    # Envoi du message sur le Webhook Discord
    payload = {"content": final_message}
    response = requests.post(webhook_url, json=payload)

    if response.status_code not in [200, 204]:
        print(f"❌ Erreur lors de l'envoi Discord (Code {response.status_code}) : {response.text}")
        sys.exit(1)
    else:
        print("✅ Rapport de marché envoyé avec succès sur Discord !")

if __path__ == "__main__":
    main()
