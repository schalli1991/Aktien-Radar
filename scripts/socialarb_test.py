"""Backtest Social-Arbitrage-Radar: Sagt ein starker Anstieg der Aufmerksamkeit (Wikipedia-Aufrufe)
künftige Überrenditen voraus, besonders wenn der Kurs noch nicht reagiert hat und die Firma klein ist?

Signale (wöchentlich, freitags):
  Sprung:  Ø Aufrufe der letzten 28 Tage / Median der 180 Tage davor
  Trend:   Ø Aufrufe der letzten 90 Tage / Ø derselben 90 Tage im Vorjahr (saisonbereinigt, träger)
Ergebnis: Überrendite gegenüber allen Aktien am selben Tag (gleich gewichtet) nach 20/60/120 Handelstagen.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import regeltest as RT  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
pd.set_option("display.width", 220)


def main():
    kurse, P, I = RT.panel()
    A = pd.read_parquet(ROOT / "daten" / "aufmerksamkeit.parquet")
    A.index = pd.to_datetime(A.index)
    mw = pd.read_csv(ROOT / "daten" / "marktwert.csv", sep=";").set_index("ticker")["marktwert_usd"]
    cols = [c for c in P.columns if c in A.columns and A[c].notna().sum() > 500]
    P, A = P[cols], A[cols].reindex(pd.date_range(A.index.min(), A.index.max())).astype(float)
    print(f"{len(cols)} Titel mit Kurs und Aufmerksamkeit, {A.index.min().date()} bis {A.index.max().date()}")
    a28 = A.rolling(28, min_periods=20).mean()
    b180 = A.shift(28).rolling(180, min_periods=120).median()
    sprung = a28 / b180
    a90 = A.rolling(90, min_periods=70).mean()
    trend = a90 / a90.shift(365)
    level = a28
    fr = [d for d in P.index if d.weekday() == 4 and d >= pd.Timestamp("2016-07-01")]
    lp = np.log(P)
    ew_lp = np.log((1 + P.pct_change(fill_method=None).mean(axis=1).fillna(0)).cumprod())
    c1m = P / P.shift(21) - 1
    rows = []
    for h in (20, 60, 120):
        fwd = lp.shift(-h) - lp
        fwd_ex = fwd.sub(ew_lp.shift(-h) - ew_lp, axis=0)
        for d in fr:
            if d not in sprung.index:
                continue
            s, tr, lv = sprung.loc[d], trend.loc[d] if d in trend.index else None, level.loc[d]
            fx = fwd_ex.loc[d]
            cm = c1m.loc[d]
            for t in cols:
                if np.isnan(fx[t]) or np.isnan(s[t]) or lv[t] < 100:
                    continue
                rows.append((d, t, h, s[t], tr[t] if tr is not None else np.nan, cm[t], fx[t]))
    df = pd.DataFrame(rows, columns=["d", "t", "h", "sprung", "trend", "c1m", "ex"])
    df["groesse"] = pd.qcut(df["t"].map(mw).rank(method="first"), 3, labels=["klein", "mittel", "gross"])
    df["kurs"] = pd.cut(df["c1m"], [-9, -0.10, 0.10, 9], labels=["gefallen", "ruhig", "gestiegen"])
    df["periode"] = np.where(df["d"] < "2021-01-01", "2016–2020", "2021–2026")
    df["sb"] = pd.cut(df["sprung"], [0, 0.8, 1.25, 2, 3, 1e9], labels=["<0.8", "0.8–1.25", "1.25–2", "2–3", "3+"])
    df["tb"] = pd.cut(df["trend"], [0, 0.7, 1.0, 1.5, 2.5, 1e9], labels=["<0.7", "0.7–1", "1–1.5", "1.5–2.5", "2.5+"])

    def tab(by, wert="ex"):
        g = df.groupby(["h"] + by, observed=True)[wert]
        o = pd.DataFrame({"n": g.size(), "mittel_%": g.mean() * 100, "median_%": g.median() * 100,
                          "positiv_%": g.apply(lambda x: (x > 0).mean() * 100)})
        return o.round(2)
    print("\n== Sprung (28 T vs. 180 T) – Überrendite ggü. allen Aktien"); print(tab(["sb"]).to_string())
    print("\n== Sprung nach Periode"); print(tab(["periode", "sb"]).unstack("periode").to_string())
    print("\n== Sprung ≥ 2: nach Kursreaktion und Grösse")
    df2 = df[df["sprung"] >= 2]
    g = df2.groupby(["h", "kurs", "groesse"], observed=True)["ex"]
    print(pd.DataFrame({"n": g.size(), "mittel_%": g.mean() * 100, "median_%": g.median() * 100}).round(2).to_string())
    print("\n== Trend (90 T vs. Vorjahr)"); print(tab(["tb"]).to_string())
    print("\n== Trend nach Periode"); print(tab(["periode", "tb"]).unstack("periode").to_string())
    print("\n== Trend ≥ 1.5 und Kurs ruhig, nach Grösse")
    df3 = df[(df["trend"] >= 1.5) & (df["kurs"] == "ruhig")]
    g = df3.groupby(["h", "groesse"], observed=True)["ex"]
    print(pd.DataFrame({"n": g.size(), "mittel_%": g.mean() * 100, "median_%": g.median() * 100}).round(2).to_string())
    df.to_parquet("/tmp/socialarb_rows.parquet")


if __name__ == "__main__":
    main()
