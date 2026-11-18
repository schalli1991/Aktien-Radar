# Social-Arbitrage-Radar – Test mit Wikipedia-Aufrufen (Stand 18.11.2026)

Idee nach Chris Camillo: Eine grosse Veränderung im Verhalten der Leute zeigt sich früh in der öffentlichen Aufmerksamkeit, bevor der Kurs reagiert. Als frei verfügbaren, täglichen Proxy mit langer Historie habe ich die Aufrufe des englischen Wikipedia-Artikels jeder Firma genommen (ab Juli 2015). Ausgewertet wurden 337 Yuh-Aktien mit korrekter Artikel-Zuordnung, Stichtage wöchentlich ab Juli 2016.

Gemessen wird die Überrendite gegenüber allen Aktien. Weil das gleich gewichtete Vergleichsportfolio laufend umschichtet, liegt der Durchschnitt aller Fälle unter null (bei 120 Tagen etwa −3 %). Entscheidend ist der Abstand zu dieser normalen Gruppe (Faktor 0,8–1,25).

## Signal 1: Sprung (Aufrufe der letzten 28 Tage im Vergleich zu den 180 Tagen davor)

| Sprung | 120 Tage, 2016–2020 | 120 Tage, 2021–2026 |
|---|---|---|
| normal (0,8–1,25) | −2,7 % | −3,1 % |
| 2–3-fach | +4,7 % | −3,6 % |
| über 3-fach | +4,9 % | −5,7 % |

Bis 2020 positiv, seit 2021 negativ. Kein stabiles Signal. Ein Sprung bei kleinen Firmen, deren Kurs gleichzeitig gefallen ist (meist schlechte Nachrichten), war ein Warnzeichen: −19 % über 120 Tage.

## Signal 2: Trend (Aufrufe der letzten 90 Tage im Vergleich zu denselben 90 Tagen im Vorjahr)

| Trend | 120 Tage, 2016–2020 | 120 Tage, 2021–2026 |
|---|---|---|
| normal (1–1,5) | −2,7 % | −3,3 % |
| 1,5–2,5-fach | +4,0 % | −1,3 % |
| über 2,5-fach | +7,0 % | −1,5 % |

In beiden Zeiträumen besser als die normale Gruppe, seit 2021 aber nur noch um etwa 2 Prozentpunkte. Das Signal hängt kaum mit dem Momentum zusammen (Rangkorrelation 0,1). Innerhalb des stärksten Momentum-Drittels war der Vorsprung am grössten (2016–2020 +9,6 % gegenüber +0,1 %, 2021–2026 +3,0 % gegenüber −2,5 %). Entgegen Camillos These schnitten grosse Firmen besser ab als kleine.

## Als Handelsregel umgesetzt (monatlich, 1,5 % Gebühr, 306 Titel mit langer Historie)

| Regel | 2016–2020 | 2021–2026 | Jahre besser als Momentum allein |
|---|---|---|---|
| Momentum-Puffer (heutige Regel) | 41,2 % p. a. | 23,3 % p. a. | – |
| Momentum Top 40, davon die mit Aufmerksamkeit ≥ 1,5 | 35,2 % | 24,0 % | 4 von 11 |
| Momentum Top 40, Aufmerksamkeit ≥ 1,2 | 32,7 % | 14,1 % | 3 von 11 |
| Momentum Top 60, Aufmerksamkeit ≥ 1,5 | 38,2 % | 23,3 % | 5 von 11 |
| Nur Aufmerksamkeit (Top 20 nach Trend) | 17,3 % | 8,6 % | 1 von 11 |
| Alle Aktien gleich gewichtet | 16,8 % | 9,9 % | – |

(Absolute Werte durch die Titelauswahl stark geschönt, siehe `regeltest.md`; aussagekräftig ist der Vergleich der Zeilen.)

## Folgerung

Wikipedia-Aufrufe liefern keinen Vorteil, der sich mit Yuh-Gebühren handeln lässt. Als Filter auf die Momentum-Liste verschlechtern sie das Ergebnis eher, als alleiniger Rang liegen sie auf dem Niveau aller Aktien. Im Dashboard erscheint die Aufmerksamkeit deshalb nur als Information in der Tabelle, nicht als Signal.

Skripte: `scripts/aufmerksamkeit_holen.py`, `scripts/socialarb_test.py`, `scripts/socialarb_portfolio.py`.
