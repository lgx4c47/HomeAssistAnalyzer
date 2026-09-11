import glob
from datetime import datetime, timedelta
import drawer_lite

"""
Ordnet die Messwerte aus dem HomeAssistant-Export in JSON für Analyse und Darstellung: 
data = {"messungen": [(DATETIME, NAME, ART, WERT], [...], ...), "meta": {"datei": NAME, "zeilen": ANZAHL, "unverwertbar": ANZAHL}}
Anschließend übergabe an Drawer für Erstellung der Auswertung. 
"""

def load_call():
    """Analysiert alle Dateien im Verzeichnis raw."""
    for datei in glob.glob("./raw/*"):
        analyze(datei)


def analyze(file: str):
    """Liest Sensordaten ein und erstellt die PDF-Auswertung."""
    data = {
        "messungen": [],
        "meta": {},
    }
    linecount = 0
    useless_lines = []

    with open(file) as rawfile:
        for linecount, line in enumerate(rawfile, start=1):
            """line kommt als: sensor.ORT_ART,WERT, 2025-12-31T23:00:00.000Z"""
            arr = line.strip().split(",")

            if len(arr) < 3:
                useless_lines.append(linecount)
                continue

            sensor = arr[0]

            if sensor.endswith("_temperatur"):
                art = "temperatur"
            elif sensor.endswith("_luftfeuchtigkeit"):
                art = "luftfeuchtigkeit"
            else:
                useless_lines.append(linecount)
                continue

            try:
                name = sensor.split('_')[0].split('.')[1]
                zeit = datetime.strptime(arr[2].replace("T", " ").replace("Z", ""), "%Y-%m-%d %H:%M:%S.%f")
                wert = float(arr[1])
            except ValueError:
                useless_lines.append(linecount)
                continue

            data["messungen"].append((zeit, name, art, wert))

    dateiname = (
        file
        .replace("/", "")
        .replace("\\", "")
        .replace(".", "-")
        .replace(" ", "_")
    )

    data["meta"] = {
        "datei": dateiname,
        "zeilen": linecount,
        "unverwertbar": len(useless_lines)
    }

    drawer_lite.erstelle_wochenauswertung(
        data,
        f'./auswertung/Auswertung_{data["meta"]["datei"]}.pdf',
    )

if __name__ == "__main__":
    load_call()