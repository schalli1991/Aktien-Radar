# Aktien-Radar

Datenquelle für den Aktien-Tab im Krypto-Radar-Dashboard.

- `config/yuh_aktien.csv`: alle bei Yuh handelbaren Aktien mit Yahoo-Kürzel und Thema. Thema ändern oder Titel ergänzen: Zeile bearbeiten.
- `config/zusatz_aktien.csv`: weitere Aktien, die nicht bei Yuh gelistet sind, aber trotzdem ins Dashboard sollen.
- `config/indizes.csv`: Indizes für die Marktlage.
- `scripts/`: Skripte, die bei GitHub laufen (Kurse holen, Risk Aktien berechnen).
- `berichte/`: Prüf- und Backtest-Berichte.

Kursdaten: Yahoo Finance über yfinance, Tagesschlusskurse.
