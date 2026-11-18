"""Täglicher Lauf: Kurse aktualisieren, Momentum-Rangliste mit Puffer, Themen, KI-Barometer, Risk Aktien,
Aufmerksamkeit (Social Arbitrage). Schreibt site/aktien.json für GitHub Pages.

Momentum-Regel (siehe berichte/regeltest.md): Rang nach Kursanstieg 12 Monate ohne letzten Monat,
monatlich zum letzten Handelstag des Monats. Kaufen: Top 20. Halten, solange Rang <= 40.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

sys.path.insert(0, str(Path(__file__).parent))
from risk_aktien_kern import bereinige, risk_serie  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
BESTAND = ROOT / "daten" / "momentum_bestand.json"
TOP, PUFFER, LB, SKIP = 20, 40, 252, 21
MODELL = "C-vol-ema10"


def r2(x, n=2):
    return None if x is None or (isinstance(x, float) and not np.isfinite(x)) else round(float(x), n)


def universum():
    teile = []
    for f, yuh in (("yuh_aktien.csv", True), ("zusatz_aktien.csv", False)):
        p = ROOT / "config" / f
        if p.exists():
            d = pd.read_csv(p, sep=";", dtype=str).fillna("")
            d["yuh"] = yuh
            teile.append(d)
    u = pd.concat(teile).drop_duplicates("ticker").set_index("ticker")
    idx = pd.read_csv(ROOT / "config" / "indizes.csv", sep=";", dtype=str).fillna("").set_index("ticker")
    ki = pd.read_csv(ROOT / "config" / "ki_themen.csv", sep=";", dtype=str)
    return u, idx, ki


def kurse_laden(tickers):
    basis = pd.read_parquet(ROOT / "daten" / "kurse.parquet") if (ROOT / "daten" / "kurse.parquet").exists() else pd.DataFrame()
    neu = {}
    for i in range(0, len(tickers), 50):
        teil = tickers[i:i + 50]
        for versuch in range(3):
            try:
                df = yf.download(teil, period="3y", interval="1d", auto_adjust=False, actions=False,
                                 group_by="column", threads=True, progress=False, repair=True)
                break
            except Exception as e:  # noqa: BLE001
                print("Fehler", e)
                time.sleep(10)
        else:
            continue
        if df is None or df.empty:
            continue
        c = df["Close"]
        for t in teil:
            if t in c.columns and c[t].notna().any():
                s = c[t].dropna()
                s.index = pd.to_datetime(s.index).tz_localize(None).normalize()
                neu[t] = s
        time.sleep(1)
    out = {}
    for t in tickers:
        a = basis[t].dropna() if t in basis.columns else pd.Series(dtype=float)
        b = neu.get(t, pd.Series(dtype=float))
        s = b if len(b) > 300 else (pd.concat([a[a.index < b.index.min()], b]) if len(b) else a)
        s = bereinige(s[~s.index.duplicated(keep="last")].sort_index())
        if len(s):
            out[t] = s
    return out


def momentum_tabelle(K: dict[str, pd.Series], datum: pd.Timestamp) -> pd.Series:
    m = {}
    for t, s in K.items():
        s = s[s.index <= datum]
        if len(s) > LB and (datum - s.index[-1]).days <= 7:
            m[t] = s.iloc[-1 - SKIP] / s.iloc[-1 - LB] - 1
    return pd.Series(m).dropna()


def monatsenden(K) -> list[pd.Timestamp]:
    alle = pd.DatetimeIndex(sorted(set().union(*[s.index for s in K.values()])))
    me = alle.to_series().groupby(alle.to_period("M")).max()
    letzte = alle[-1]
    return [d for d in me if d < letzte or d.to_period("M") < letzte.to_period("M")]


def puffer_schritt(alt: list[str], mom: pd.Series) -> list[str]:
    rk = mom.rank(ascending=False)
    halt = [t for t in alt if t in rk.index and rk[t] <= PUFFER]
    for t in mom.nlargest(TOP).index:
        if len(halt) >= TOP:
            break
        if t not in halt:
            halt.append(t)
    return halt


def bestand_aktualisieren(K, yuh_tickers):
    Ky = {t: s for t, s in K.items() if t in yuh_tickers}
    me = monatsenden(Ky)
    st = json.loads(BESTAND.read_text()) if BESTAND.exists() else {"monat": None, "titel": [], "historie": []}
    if st["monat"] is None:  # Erstlauf: Puffer-Regel ab Januar 2024 durchspielen, damit der Bestand konsistent ist
        todo = [d for d in me if d >= pd.Timestamp("2024-01-01")]
    else:
        todo = [d for d in me if str(d.to_period("M")) > st["monat"]]
    for d in todo:
        mom = momentum_tabelle(Ky, d)
        if len(mom) < PUFFER:
            continue
        neu = puffer_schritt(st["titel"], mom)
        st["historie"].append({"monat": str(d.to_period("M")), "datum": str(d.date()),
                               "rein": [t for t in neu if t not in st["titel"]],
                               "raus": [t for t in st["titel"] if t not in neu]})
        st["titel"], st["monat"] = neu, str(d.to_period("M"))
    st["historie"] = st["historie"][-24:]
    BESTAND.write_text(json.dumps(st, indent=1))
    return st


def woechentlich(s: pd.Series, n=105):
    w = s.resample("W-FRI").last().dropna().tail(n)
    return [str(w.index[0].date()) if len(w) else None, [r2(x, 4 if x < 10 else 2) for x in w.values]]


def aufmerksamkeit_frisch():
    zp = ROOT / "config" / "wikipedia.csv"
    if not zp.exists():
        return None
    import requests
    from urllib.parse import quote
    z = pd.read_csv(zp, sep=";", dtype=str).fillna("")
    ses = requests.Session()
    ses.headers["User-Agent"] = "aktien-radar/1.0 (https://github.com/schalli1991/Aktien-Radar)"
    ende = pd.Timestamp.utcnow().tz_localize(None).normalize() - pd.Timedelta(days=1)
    start = ende - pd.Timedelta(days=400)
    ser = {}
    for _, r in z.iterrows():
        art = r["fix"] or r["artikel"]
        if not art:
            continue
        url = ("https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user/"
               f"{quote(art, safe='')}/daily/{start:%Y%m%d}/{ende:%Y%m%d}")
        try:
            res = ses.get(url, timeout=30)
            if res.ok:
                it = res.json().get("items", [])
                ser[r["ticker"]] = pd.Series({pd.Timestamp(x["timestamp"][:8]): x["views"] for x in it}, dtype=float)
        except Exception:  # noqa: BLE001
            pass
    return pd.DataFrame(ser).sort_index() if ser else None


def aufmerksamkeit():
    a = aufmerksamkeit_frisch()
    if a is None:
        p = ROOT / "daten" / "aufmerksamkeit.parquet"
        if not p.exists():
            return {}, None
        a = pd.read_parquet(p)
    out = {}
    for t in a.columns:
        s = a[t].dropna()
        if len(s) < 240:
            continue
        akt = s.tail(28).mean()
        basis = s.iloc[-208:-28].median()
        if basis and basis > 0:
            out[t] = {"aufrufe28": r2(akt, 0), "basis180": r2(basis, 0), "faktor": r2(akt / basis, 2),
                      "woche": woechentlich(s.resample("W-FRI").sum(), 53)}
    return out, str(a.index[-1].date())


def main():
    u, idx, ki = universum()
    tickers = list(u.index) + list(idx.index)
    K = kurse_laden(tickers)
    mod = json.loads((ROOT / "modell" / "varianten.json").read_text())[MODELL]
    yuh = set(u.index[u["yuh"]])
    st = bestand_aktualisieren(K, set(u.index))
    letzte = max(s.index[-1] for s in K.values())
    mom_heute = momentum_tabelle({t: K[t] for t in u.index if t in K}, letzte)
    rk_heute = mom_heute.rank(ascending=False)
    me_letzt = pd.Timestamp(st["historie"][-1]["datum"]) if st["historie"] else letzte
    mom_me = momentum_tabelle({t: K[t] for t in u.index if t in K}, me_letzt)
    rk_me = mom_me.rank(ascending=False)
    att, att_stand = aufmerksamkeit()
    mw = pd.read_csv(ROOT / "daten" / "marktwert.csv", sep=";").set_index("ticker") if (ROOT / "daten" / "marktwert.csv").exists() else pd.DataFrame()
    ki_map = ki.groupby("ticker")["ki_thema"].apply(list).to_dict()

    titel, risk_akt, ueber200 = {}, {}, {}
    for t in u.index:
        if t not in K:
            continue
        s = K[t]
        if (letzte - s.index[-1]).days > 10 or len(s) < 30:
            continue
        r = risk_serie(s, mod) if len(s) > 400 else pd.Series(np.nan, index=s.index)
        sma200 = s.rolling(200).mean()
        p = s.iloc[-1]

        def chg(n):
            return r2((p / s.iloc[-1 - n] - 1) * 100, 1) if len(s) > n else None
        ra = r.iloc[-1]
        risk_akt[t] = ra
        ueber200[t] = bool(p > sma200.iloc[-1]) if np.isfinite(sma200.iloc[-1]) else None
        status = "halten" if t in st["titel"] else None
        if st["historie"] and t in st["historie"][-1]["rein"]:
            status = "neu"
        rec = {
            "n": u.at[t, "name"], "th": u.at[t, "thema"], "ki": ki_map.get(t, []), "b": u.at[t, "boerse"],
            "w": u.at[t, "waehrung"], "yuh": bool(u.at[t, "yuh"]), "p": r2(p, 4 if p < 10 else 2),
            "c1m": chg(21), "c3m": chg(63), "c6m": chg(126), "c12m": chg(252),
            "mom": r2(mom_heute.get(t, np.nan) * 100, 1), "rk": r2(rk_heute.get(t, np.nan), 0),
            "rkMe": r2(rk_me.get(t, np.nan), 0), "st": status,
            "risk": r2(ra, 0), "risk1m": r2(r.iloc[-22], 0) if len(r) > 22 else None,
            "u200": ueber200[t], "d200": r2((p / sma200.iloc[-1] - 1) * 100, 1) if np.isfinite(sma200.iloc[-1]) else None,
            "kurs": woechentlich(s), "rs": woechentlich(r.dropna()) if r.notna().any() else None,
        }
        if t in mw.index and pd.notna(mw.at[t, "marktwert_usd"]):
            rec["mcap"] = r2(mw.at[t, "marktwert_usd"] / 1e9, 2)
        if t in att:
            a = att[t]
            rec["att"] = {k: a[k] for k in ("aufrufe28", "basis180", "faktor")}
            rec["attW"] = a["woche"]
        titel[t] = rec
    raus = [t for t in (st["historie"][-1]["raus"] if st["historie"] else []) if t in titel]
    for t in raus:
        titel[t]["st"] = "raus"

    # Themen und KI-Barometer: gleich gewichtete Körbe
    def korb(members):
        m = [t for t in members if t in titel]
        if len(m) < 2:
            return None
        def avg(k):
            v = [titel[t][k] for t in m if titel[t][k] is not None]
            return r2(np.mean(v), 1) if v else None
        rs = [titel[t]["risk"] for t in m if titel[t]["risk"] is not None]
        uu = [titel[t]["u200"] for t in m if titel[t]["u200"] is not None]
        return {"n": len(m), "c1m": avg("c1m"), "c3m": avg("c3m"), "c6m": avg("c6m"), "c12m": avg("c12m"),
                "risk": r2(np.median(rs), 0) if rs else None, "u200": r2(np.mean(uu) * 100, 0) if uu else None,
                "titel": sorted(m, key=lambda t: titel[t]["rk"] if titel[t]["rk"] is not None else 999)}
    alle = korb(list(titel))
    themen = {th: korb(list(g.index)) for th, g in u.groupby("thema")}
    themen = {k: v for k, v in themen.items() if v}
    kib = {th: korb(list(g["ticker"])) for th, g in ki.groupby("ki_thema")}
    kib = {k: v for k, v in kib.items() if v}
    for d in (themen, kib):
        for v in d.values():
            v["rel6m"] = r2((v["c6m"] or 0) - (alle["c6m"] or 0), 1)
            v["rel3m"] = r2((v["c3m"] or 0) - (alle["c3m"] or 0), 1)

    markt = {}
    for t in idx.index:
        if t in K:
            s = K[t]
            r = risk_serie(s, mod)
            sm = s.rolling(200).mean().iloc[-1]
            markt[t] = {"n": idx.at[t, "name"], "p": r2(s.iloc[-1]), "c1m": r2((s.iloc[-1] / s.iloc[-22] - 1) * 100, 1),
                        "c12m": r2((s.iloc[-1] / s.iloc[-253] - 1) * 100, 1), "risk": r2(r.iloc[-1], 0),
                        "u200": bool(s.iloc[-1] > sm), "kurs": woechentlich(s)}
    breite = r2(np.mean([v for v in ueber200.values() if v is not None]) * 100, 0)

    out = {
        "stand": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "kurseBis": str(letzte.date()),
        "regel": {"top": TOP, "puffer": PUFFER, "lookback": "12 Monate ohne letzten Monat", "monat": st["monat"],
                  "stichtag": str(me_letzt.date())},
        "bestand": st["titel"], "historie": st["historie"][-12:],
        "markt": markt, "breite": breite, "alle": {k: v for k, v in alle.items() if k != "titel"},
        "themen": themen, "ki": kib, "attStand": att_stand, "titel": titel,
    }
    SITE.mkdir(exist_ok=True)
    (SITE / "aktien.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    (SITE / "index.html").write_text("<!doctype html><meta charset=utf-8><title>Aktien-Radar Daten</title>"
                                     f"<p>Aktien-Radar Datenquelle. Stand {out['stand']}. <a href='aktien.json'>aktien.json</a></p>",
                                     encoding="utf-8")
    print(f"Fertig: {len(titel)} Titel, Bestand {len(st['titel'])}, Stichtag {me_letzt.date()}, "
          f"Datei {(SITE / 'aktien.json').stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
