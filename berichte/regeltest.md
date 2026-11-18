# Aktien-taugliche Regeln – Test (Stand 18.11.2026)

Universum: 344 Yuh-Aktien mit genug Kurshistorie, Tagesschlusskurse. Gebühr 0,5 % pro Kauf und Verkauf (Yuh-Courtage), wo vermerkt 1,5 % (Courtage plus 0,95 % Devisenzuschlag bei Titeln in Fremdwährung). Signal am Tagesschluss, Ausführung ab dem Folgetag. Zwei getrennte Zeiträume: 2005–2018 und 2019–18.11.2026. Risk Aktien: Variante C-vol-ema10 aus `kalibrierung.md`.

**Wichtige Einschränkung:** Die Liste enthält nur Firmen, die heute bei Yuh handelbar sind. Pleiten und Übernahmen der Vergangenheit fehlen, und Yuh hat in den letzten Jahren gezielt Titel aufgenommen, die bereits stark gestiegen waren (z. B. Palantir, AppLovin, IonQ). Das schönt alle Ergebnisse, Momentum-Strategien besonders. Die echten Vorteile dürften kleiner sein.

## 1. Timing-Regeln je Aktie (ein- oder aussteigen)

Gleich gewichtetes Portfolio aller Aktien, jede Aktie folgt der Regel.

| Regel | Zeitraum | Rendite p. a. | Max. Rückgang | Schlägt Halten bei | Median Endvermögen ggü. Halten |
|---|---|---|---|---|---|
| Halten | 2005–2018 | 10,2 % | −54 % | – | 1,00 |
| Halten | 2019–2026 | 13,5 % | −35 % | – | 1,00 |
| Trendfilter 200 Tage | 2005–2018 | 5,3 % | −21 % | 26 % der Aktien | 0,64 |
| Trendfilter 200 Tage | 2019–2026 | 5,6 % | −14 % | 21 % | 0,67 |
| Trendbruch (SMA50) nach Risk 90 | 2005–2018 | 9,1 % | −54 % | 12 % | 0,87 |
| Trendbruch (SMA50) nach Risk 90 | 2019–2026 | 12,6 % | −33 % | 24 % | 0,92 |
| Halbe Position ab Risk 95 | 2005–2018 | 10,0 % | −54 % | 39 % | 1,00 |
| Halbe Position ab Risk 95 | 2019–2026 | 13,4 % | −35 % | 44 % | 1,00 |
| Marktfilter (Heimindex über 200 Tage) | 2005–2018 | 5,2 % | −20 % | 27 % | 0,60 |
| Marktfilter (Heimindex über 200 Tage) | 2019–2026 | 4,4 % | −22 % | 9 % | 0,58 |

Keine Timing-Regel schlägt das Halten. Trend- und Marktfilter verringern die Rückgänge stark, kosten aber etwa die Hälfte der Rendite.

**Einstieg bei tiefem Risk (< 20) plus Wende** (Schluss über SMA20): Überrendite gegenüber dem eigenen Durchschnitt nach 60 Tagen −3,2 % (2005–2018) bzw. +2,9 % (2019–2026), nach 250 Tagen +1,6 % bzw. +8,2 %, Trefferquote 42–58 %. Kein stabiler Vorteil.

## 2. Rotation: monatlich die 20 Aktien mit dem stärksten Momentum

Momentum = Kursanstieg der letzten 12 Monate ohne den letzten Monat. Vergleich: alle Aktien gleich gewichtet (EW).

| Variante | Zeitraum | Rendite p. a. | EW | Max. Rückgang (EW) | Jahre besser als EW |
|---|---|---|---|---|---|
| Top 20, monatlich, 0,5 % | 2005–2018 | 18,5 % | 10,5 % | −51 % (−54 %) | 12 von 14 |
| Top 20, monatlich, 0,5 % | 2019–2026 | 40,3 % | 13,7 % | −44 % (−36 %) | 7 von 8 |
| Top 20, monatlich, 1,5 % | 2005–2018 | 11,3 % | 10,5 % | −55 % (−54 %) | 8 von 14 |
| Top 20, monatlich, 1,5 % | 2019–2026 | 31,8 % | 13,7 % | −51 % (−36 %) | 5 von 8 |
| **Puffer: Top 20 kaufen, halten bis Rang > 40, 1,5 %** | 2005–2018 | **14,7 %** | 10,5 % | −54 % (−54 %) | 10 von 14 |
| **Puffer, 1,5 %** | 2019–2026 | **35,4 %** | 13,7 % | −41 % (−36 %) | 6 von 8 |
| Puffer, nur Titel mit Kursen vor 2015 | 2005–2018 | 13,6 % | 10,3 % | −54 % (−54 %) | 9 von 14 |
| Puffer, nur Titel mit Kursen vor 2015 | 2019–2026 | 23,2 % | 12,8 % | −39 % (−36 %) | 5 von 8 |
| Puffer, nur Schweiz und Europa | 2005–2018 | 8,2 % | 7,3 % | −53 % (−57 %) | 10 von 14 |
| Puffer, nur Schweiz und Europa | 2019–2026 | 10,9 % | 8,1 % | −36 % (−37 %) | 3 von 8 |
| Top 20 + Marktfilter S&P 500 | 2005–2018 | 22,6 % | 10,4 % | −24 % (−54 %) | – |
| Top 20 + Marktfilter S&P 500 | 2019–2026 | 20,8 % | 13,6 % | −45 % (−36 %) | – |
| Tiefster Risk über SMA200, Top 20 | 2005–2018 | −0,7 % | 10,4 % | −59 % | – |
| Tiefster Risk über SMA200, Top 20 | 2019–2026 | 3,4 % | 13,6 % | −34 % | – |

Momentum-Rotation ist der einzige Ansatz, der in beiden Zeiträumen und nach realistischen Kosten vorne liegt. Die Puffer-Regel halbiert den Umschlag (rund 3,5-mal pro Jahr statt 6,4-mal) und ist deshalb für Yuh-Gebühren die sinnvolle Form. Der Vorsprung 2005–2018 von rund 4 Prozentpunkten pro Jahr ist plausibel und passt zur Fachliteratur. Die Werte für 2019–2026 sind durch die Titelauswahl stark geschönt. Rückgänge im Crash schützt Momentum nicht ab. Bei Schweizer und europäischen Titeln allein ist der Vorteil klein.

Skripte: `scripts/regeltest.py`, `scripts/regeltest_robust.py`; Rohwerte: `berichte/regeltest_tabelle.csv`.
