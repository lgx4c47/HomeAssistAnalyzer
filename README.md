# Wohnungsklima-Auswertung

Kleines Python-Tool zur Auswertung und grafischen Darstellung von
Temperatur- und Luftfeuchtigkeitsmessungen.

Die Messdaten werden eingelesen, nach Kalenderwochen aufbereitet und als
PDF-Dokument mit Diagrammen ausgegeben.

## Funktionen

- Einlesen von Temperatur- und Luftfeuchtigkeitsdaten
- Aufteilung nach Kalenderwochen
- Darstellung mehrerer Sensoren
- Temperatur-Orientierungslinien bei 18 °C, 20 °C und 21 °C
- Ausgabe als DIN-A4-PDF
- getrennte Temperatur- und Luftfeuchtigkeitsseiten
- Notizbereich auf den Diagrammseiten
- kurzer technischer Report zur Verarbeitung der Eingabedatei

## Projektstruktur

```text
.
├── main_lite.py
├── drawer_lite.py
├── raw/
├── alte rawdaten/
├── analyzed/
├── diagramme/
└── auswertung

## Einschränkungen: 

Funktioniert nur mit Messdaten auf Deutsch und Sensorwerten. 