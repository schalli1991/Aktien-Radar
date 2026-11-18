# Risk Aktien – Kalibrierung und Backtest (Stand 18.11.2026)

Datengrundlage: 344 Yuh-Aktien mit mindestens 600 Handelstagen, Tagesschlusskurse von Yahoo (split-bereinigt), 1995 bis 18.11.2026. Gelernt wurde bis Ende 2018, geprüft auf 2019 bis heute. Die Liste enthält nur Firmen, die heute noch gehandelt werden (Survivorship-Bias).

## Methode

Wie Risk v2: log-Abstand des Kurses zu vier gleitenden Durchschnitten, Gewichte per logistischer Regression auf Swing-Hochs und -Tiefs, Umrechnung in ein Perzentil aller Trainingstage, Glättung per EMA, gleiche Skala (80 = oberste 10 %, 90 = oberste 5 %, 20 = unterste 5 %). Ein Swing-Hoch ist ein 80-Tage-Hoch, nach dem der Kurs innert 120 Handelstagen um mindestens 10 % bzw. 2 Tagesvolatilitäten × √60 fiel; Tiefs spiegelbildlich.

Geprüfte Varianten:

| Fenster | Handelstage |
|---|---|
| A | 14 / 35 / 100 / 250 (Krypto-Längen in Handelstage umgerechnet) |
| B | 20 / 50 / 100 / 200 (klassische Aktien-Durchschnitte) |
| C | 20 / 50 / 140 / 350 (Risk-v2-Längen, auf Handelstage angewendet) |

Jeweils roh oder durch die eigene Volatilität (250 Tage) geteilt, mit 5- oder 10-Tage-EMA.

## Ergebnisse

**Risk v2 unverändert passt nicht auf Aktien.** Im Test lagen nur 0,4 % aller Tage bei 80 oder höher und 0,5 % unter 20. Die Skala wird praktisch nie ausgenutzt.

**Ohne Volatilitäts-Normierung verzerrt.** Bei den Roh-Varianten lagen ruhige Aktien an 4 % der Tage über 80, volatile an 18 %. Mit Normierung sind es in allen drei Volatilitätsgruppen 7–10 %. Die Normierung ist deshalb Pflicht.

**Das Überhitzungssignal ist bei Aktien nicht stabil.** Überrendite gegenüber dem eigenen Durchschnitt der Aktie, Variante C-vol-ema10, in Prozent:

| Zeitraum | Horizont | Risk < 10 | 10–20 | 20–50 | 50–80 | 80–90 | 90–95 | 95+ |
|---|---|---|---|---|---|---|---|---|
| 1995–2018 | 60 Tage | +0,8 | −0,3 | −0,3 | +0,1 | +0,7 | +0,6 | +2,0 |
| 2019–2026 | 60 Tage | +7,0 | +3,2 | +0,5 | −0,7 | −0,9 | −0,6 | −2,5 |
| 2019–2026 ohne 2020 | 60 Tage | +0,5 | +2,2 | +0,7 | −0,7 | −1,3 | −1,1 | −2,4 |
| 1995–2018 | 120 Tage | +5,5 | +0,5 | −0,4 | +0,1 | +1,3 | +1,0 | +1,1 |
| 2019–2026 | 120 Tage | +5,9 | +1,5 | +0,5 | −0,5 | −1,1 | −0,9 | −3,5 |

Bis 2018 liefen Aktien mit hohem Score im Schnitt sogar besser weiter (Momentum). Seit 2019 liefen sie leicht schlechter. Die Unterschiede liegen meist bei 1–3 % über drei bis sechs Monate. Das gute Abschneiden tiefer Scores 2019–2026 stammt grösstenteils aus dem Corona-Crash 2020.

**Die Krypto-Exit-Regel bringt bei Aktien nichts.** Simuliert: 1/3 verkaufen bei 80, 1/3 bei 90, Rest beim Rückfall unter 80, Rückkauf bei Score unter 50 bzw. unter 20, Cash ohne Zins.

| Zeitraum | Rückkauf | Regel schlägt Halten | Median Endvermögen Regel / Halten |
|---|---|---|---|
| 2005–2018 | unter 50 | 45–47 % der Aktien | 0,96–0,99 |
| 2005–2018 | unter 20 | 20–21 % | 0,58 |
| 2019–2026 | unter 50 | 53–56 % | 1,03–1,04 |
| 2019–2026 | unter 20 | 36–37 % | 0,82–0,84 |

## Folgerung

Risk Aktien (vol-normiert, Fenster C, 10-Tage-EMA) ordnet sauber ein, wie weit eine Aktie im Verhältnis zur eigenen Schwankung gelaufen ist, und verteilt sich fair über ruhige und volatile Titel. Als mechanisches Verkaufssignal taugt er bei Aktien nicht: Der Effekt ist klein und hat zwischen den Jahrzehnten das Vorzeichen gewechselt.

Rohdaten aller Varianten: `berichte/kalibrierung_tabelle.csv`, Gewichte und Tabellen: `modell/varianten.json`.
