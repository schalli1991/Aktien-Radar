"""Holt die komplette Tageskurs-Historie aller Titel aus config/*.csv von Yahoo Finance.

Ergebnis:
  daten/kurse.parquet     Schlusskurse (split-bereinigt, ohne Dividendenbereinigung), Spalte je Ticker
  berichte/kurspruefung.md  Welche Titel Daten haben, welche fehlen oder nicht mehr gehandelt werden

Läuft in GitHub Actions (siehe .github/workflows/kurse_holen.yml).
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
CFG = ROOT / "config"
OUT = ROOT / "daten"
REP = ROOT / "berichte"
BATCH = 40


def universum() -> pd.DataFrame:
    teile = []
    for f in ["yuh_aktien.csv", "zusatz_aktien.csv", "indizes.csv"]:
        p = CFG / f
        if p.exists():
            d = pd.read_csv(p, sep=";", dtype=str).fillna("")
            d["quelle"] = f
            teile.append(d)
    u = pd.concat(teile, ignore_index=True)
    u["ticker"] = u["ticker"].str.strip()
    return u[u["ticker"] != ""].drop_duplicates("ticker")


def lade(tickers: list[str]) -> dict[str, pd.Series]:
    out: dict[str, pd.Series] = {}
    for i in range(0, len(tickers), BATCH):
        teil = tickers[i:i + BATCH]
        for versuch in range(3):
            try:
                df = yf.download(teil, period="max", interval="1d", auto_adjust=False,
                                 actions=False, group_by="column", threads=True, progress=False, repair=True)
                break
            except Exception as e:  # noqa: BLE001
                print(f"Fehler Batch {i}: {e}; neuer Versuch")
                time.sleep(10 * (versuch + 1))
        else:
            continue
        if df is None or df.empty:
            continue
        close = df["Close"] if isinstance(df.columns, pd.MultiIndex) else df[["Close"]].rename(columns={"Close": teil[0]})
        for t in teil:
            if t in close.columns:
                s = close[t].dropna()
                s = s[s > 0]
                if len(s):
                    out[t] = s
        print(f"{min(i + BATCH, len(tickers))}/{len(tickers)} geladen")
        time.sleep(2)
    # Einzeln nachladen, was im Batch leer blieb
    for t in [t for t in tickers if t not in out]:
        for versuch in range(2):
            try:
                h = yf.Ticker(t).history(period="max", interval="1d", auto_adjust=False, actions=False)
                s = h["Close"].dropna() if not h.empty else pd.Series(dtype=float)
                s = s[s > 0]
                if len(s):
                    out[t] = s
                break
            except Exception as e:  # noqa: BLE001
                print(f"Fehler {t}: {e}")
                time.sleep(5)
    return out


def vorschlag(name: str) -> str:
    """Bei fehlenden Daten: Yahoo-Suche nach dem Namen, um das richtige Kürzel zu finden."""
    try:
        q = yf.Search(name, max_results=5).quotes
        return ", ".join(f"{x.get('symbol')} ({x.get('exchange')})" for x in q if x.get("quoteType") == "EQUITY")
    except Exception:  # noqa: BLE001
        return ""


def main() -> None:
    OUT.mkdir(exist_ok=True)
    REP.mkdir(exist_ok=True)
    u = universum()
    tickers = u["ticker"].tolist()
    print(f"yfinance {yf.__version__}, {len(tickers)} Titel")
    serien = lade(tickers)

    frames = {}
    for t, s in serien.items():
        s = s.copy()
        s.index = pd.to_datetime(s.index).tz_localize(None).normalize()
        frames[t] = s[~s.index.duplicated(keep="last")]
    kurse = pd.DataFrame(frames).sort_index().astype("float32")
    kurse.index.name = "datum"
    kurse.to_parquet(OUT / "kurse.parquet", compression="zstd")

    heute = pd.Timestamp(datetime.now(timezone.utc).date())
    zeilen = []
    for _, r in u.iterrows():
        t = r["ticker"]
        s = kurse[t].dropna() if t in kurse.columns else pd.Series(dtype=float)
        if s.empty:
            status, start, ende, n = "keine Daten", "", "", 0
        else:
            start, ende, n = s.index[0].date(), s.index[-1].date(), len(s)
            alt = (heute - s.index[-1]).days
            status = "ok" if alt <= 7 else f"letzter Kurs vor {alt} Tagen"
        tipp = vorschlag(r["name"]) if status != "ok" else ""
        zeilen.append((t, r["name"], r["quelle"], status, start, ende, n, tipp))

    ok = sum(1 for z in zeilen if z[3] == "ok")
    md = [f"# Kursprüfung\n", f"Stand {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC · yfinance {yf.__version__}\n",
          f"{ok} von {len(zeilen)} Titeln mit aktuellen Kursen.\n",
          "\n## Probleme\n", "| Ticker | Name | Status | Vorschlag laut Yahoo-Suche |", "|---|---|---|---|"]
    md += [f"| {z[0]} | {z[1]} | {z[3]} | {z[7]} |" for z in zeilen if z[3] != "ok"]
    md += ["\n## Alle Titel\n", "| Ticker | Name | Liste | Status | Erster Kurs | Letzter Kurs | Tage |", "|---|---|---|---|---|---|---|"]
    md += [f"| {z[0]} | {z[1]} | {z[2]} | {z[3]} | {z[4]} | {z[5]} | {z[6]} |" for z in zeilen]
    (REP / "kurspruefung.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"Fertig: {ok}/{len(zeilen)} ok, Datei {OUT / 'kurse.parquet'}")


if __name__ == "__main__":
    main()
