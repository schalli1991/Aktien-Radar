"""Social-Arbitrage-Rohdaten: tägliche Wikipedia-Seitenaufrufe je Firma (ab Juli 2015) und Marktkapitalisierung.

Ergebnis:
  config/wikipedia.csv           Zuordnung Ticker → englischer Wikipedia-Artikel (von Hand korrigierbar, Spalte 'fix')
  daten/aufmerksamkeit.parquet   tägliche Seitenaufrufe, Spalte je Ticker
  daten/marktwert.csv            aktuelle Marktkapitalisierung in USD
  berichte/wikipedia_zuordnung.md  Zuordnung zur Kontrolle
"""
from __future__ import annotations

import re
import time
import unicodedata
from datetime import date, timedelta
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import quote

import pandas as pd
import requests
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
UA = {"User-Agent": "aktien-radar/1.0 (https://github.com/schalli1991/Aktien-Radar)"}
S = requests.Session()
S.headers.update(UA)

SPARQL = """
SELECT ?item ?ticker ?article WHERE {
  ?item p:P414 ?st . ?st pq:P249 ?ticker .
  ?article schema:about ?item ; schema:isPartOf <https://en.wikipedia.org/> .
}"""

RAUS = re.compile(r"\b(ag|sa|se|nv|plc|inc|corp|corporation|holding|holdings|group|co|company|ltd|the|und|&)\b")


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\(.*?\)", " ", s)
    s = RAUS.sub(" ", re.sub(r"[^a-z0-9& ]", " ", s))
    return " ".join(s.split())


def aehnlich(a: str, b: str) -> float:
    a, b = norm(a), norm(b)
    if not a or not b:
        return 0.0
    kurz, lang = (a, b) if len(a) <= len(b) else (b, a)
    if re.search(r"\b" + re.escape(kurz) + r"\b", lang):
        return 1.0 if len(kurz) >= 4 or kurz == lang else 0.7
    return SequenceMatcher(None, a, b).ratio()


def wikidata_tabelle() -> pd.DataFrame:
    for versuch in range(3):
        try:
            r = S.get("https://query.wikidata.org/sparql", params={"query": SPARQL, "format": "json"}, timeout=120)
            r.raise_for_status()
            rows = [(b["ticker"]["value"].upper(), b["article"]["value"].rsplit("/", 1)[-1])
                    for b in r.json()["results"]["bindings"]]
            return pd.DataFrame(rows, columns=["sym", "artikel"]).drop_duplicates()
        except Exception as e:  # noqa: BLE001
            print("Wikidata-Fehler:", e)
            time.sleep(20)
    return pd.DataFrame(columns=["sym", "artikel"])


def suche(name: str) -> tuple[str, float]:
    best, score = "", 0.0
    for q in (f"{name} company", name):
        try:
            r = S.get("https://en.wikipedia.org/w/api.php", timeout=30, params={
                "action": "query", "list": "search", "srsearch": q, "srlimit": 5, "format": "json"})
            for hit in r.json()["query"]["search"]:
                sc = aehnlich(name, hit["title"])
                if sc > score:
                    best, score = hit["title"].replace(" ", "_"), sc
        except Exception as e:  # noqa: BLE001
            print("Suche fehlgeschlagen:", name, e)
        if score >= 0.9:
            break
        time.sleep(0.3)
    return best, score


def zuordnung(u: pd.DataFrame) -> pd.DataFrame:
    p = ROOT / "config" / "wikipedia.csv"
    alt = pd.read_csv(p, sep=";", dtype=str).fillna("") if p.exists() else pd.DataFrame(columns=["ticker", "artikel", "methode", "fix"])
    alt = alt.set_index("ticker")
    wd = wikidata_tabelle()
    zeilen = []
    for _, r in u.iterrows():
        t, name = r["ticker"], r["name"]
        if t in alt.index and alt.at[t, "fix"]:
            zeilen.append((t, name, alt.at[t, "fix"], "von Hand", alt.at[t, "fix"]))
            continue
        sym = t.split(".")[0].replace("-", ".").upper()
        kand = wd[wd["sym"] == sym]["artikel"].tolist()
        best = max(kand, key=lambda a: aehnlich(name, a.replace("_", " ")), default="")
        if best and aehnlich(name, best.replace("_", " ")) >= 0.6:
            zeilen.append((t, name, best, "Wikidata (Ticker)", ""))
            continue
        art, sc = suche(name)
        zeilen.append((t, name, art, f"Suche ({sc:.2f})" if art else "nicht gefunden", ""))
    z = pd.DataFrame(zeilen, columns=["ticker", "name", "artikel", "methode", "fix"])
    z[["ticker", "artikel", "methode", "fix"]].to_csv(p, sep=";", index=False)
    return z


def aufrufe(artikel: str, start: str, ende: str) -> pd.Series:
    url = ("https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user/"
           f"{quote(artikel, safe='')}/daily/{start}/{ende}")
    for versuch in range(3):
        r = S.get(url, timeout=30)
        if r.status_code == 404:
            return pd.Series(dtype=float)
        if r.ok:
            it = r.json().get("items", [])
            return pd.Series({pd.Timestamp(x["timestamp"][:8]): x["views"] for x in it}, dtype=float)
        time.sleep(3 * (versuch + 1))
    return pd.Series(dtype=float)


def main():
    teile = []
    for f in ["yuh_aktien.csv", "zusatz_aktien.csv"]:
        p = ROOT / "config" / f
        if p.exists():
            teile.append(pd.read_csv(p, sep=";", dtype=str).fillna(""))
    u = pd.concat(teile).drop_duplicates("ticker")
    z = zuordnung(u)
    ende = (date.today() - timedelta(days=1)).strftime("%Y%m%d")
    serien = {}
    for _, r in z.iterrows():
        if r["artikel"]:
            s = aufrufe(r["artikel"], "20150701", ende)
            if len(s):
                serien[r["ticker"]] = s
        time.sleep(0.05)
    a = pd.DataFrame(serien).sort_index().astype("float32")
    a.index.name = "datum"
    a.to_parquet(ROOT / "daten" / "aufmerksamkeit.parquet", compression="zstd")

    mw = []
    for t in u["ticker"]:
        try:
            fi = yf.Ticker(t).fast_info
            cap, cur = fi.get("marketCap") or fi.get("market_cap"), fi.get("currency")
            mw.append((t, cap, cur))
        except Exception:  # noqa: BLE001
            mw.append((t, None, None))
    mw = pd.DataFrame(mw, columns=["ticker", "marktwert", "waehrung"])
    fx = {}
    for c in mw["waehrung"].dropna().unique():
        if c == "USD":
            fx[c] = 1.0
            continue
        try:
            h = yf.Ticker(f"{c}USD=X").history(period="5d")["Close"]
            fx[c] = float(h.iloc[-1]) if len(h) else None
        except Exception:  # noqa: BLE001
            fx[c] = None
    fx["GBp"] = (fx.get("GBP") or 0) / 100 if fx.get("GBP") else None
    mw["marktwert_usd"] = [m * fx[c] if (m and c in fx and fx[c]) else None for m, c in zip(mw["marktwert"], mw["waehrung"])]
    mw.to_csv(ROOT / "daten" / "marktwert.csv", sep=";", index=False)

    md = ["# Wikipedia-Zuordnung\n", f"{(z['artikel'] != '').sum()} von {len(z)} Titeln zugeordnet, "
          f"{len(serien)} mit Seitenaufrufen.\n", "Falsche Zuordnung korrigieren: in `config/wikipedia.csv` "
          "in der Spalte `fix` den richtigen Artikelnamen eintragen (wie in der Wikipedia-Adresse).\n",
          "| Ticker | Name | Artikel | Methode | Ø Aufrufe/Tag (letzte 90 T) |", "|---|---|---|---|---|"]
    for _, r in z.iterrows():
        s = a[r["ticker"]].dropna() if r["ticker"] in a.columns else pd.Series(dtype=float)
        md.append(f"| {r['ticker']} | {r['name']} | {r['artikel']} | {r['methode']} | {s.tail(90).mean():.0f} |" if len(s)
                  else f"| {r['ticker']} | {r['name']} | {r['artikel']} | {r['methode']} | – |")
    (ROOT / "berichte" / "wikipedia_zuordnung.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"Fertig: {len(serien)} Titel mit Aufrufen")


if __name__ == "__main__":
    main()
