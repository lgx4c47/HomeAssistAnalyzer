import textwrap
from datetime import datetime, date, timedelta
 
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_pdf import PdfPages
 
SCHWELLENWERT_TEMP = 20.0  # °C
AUSGESCHLOSSENE_SENSOREN = ("schlafzimmer",)  # zählt nicht für rote Tag-Markierung
 
 
def _parse_punkte(werte: dict) -> list:
    """macht aus Zeit- und Messwert-Strings eine sortierte (Zeit, Wert)-Liste"""
    zeiten = [datetime.strptime(z, "%Y-%m-%d %H:%M:%S.%f") for z in werte["zeit"]]
    messwerte = [float(m) for m in werte["messwert"]]
    return sorted(zip(zeiten, messwerte))
 
 
def _lade_daten(data: dict) -> dict:
    """baut aus dem Eingabe-dict {typ: {sensor: [(zeit, wert), ...]}}"""
    ergebnis: dict = {}
    for typ in ("luftfeuchtigkeit", "temperatur"):
        ergebnis[typ] = {}
        for gruppen_id, sensoren in data[typ].items():
            for sensor, werte in sensoren.items():
                schluessel = sensor if gruppen_id == 1 else f"{sensor}_{gruppen_id}"
                ergebnis[typ][schluessel] = _parse_punkte(werte)
    return ergebnis
 
 
def _sensor_label(sensor: str, typ: str) -> str:
    """kürzt Sensor-Namen für die Legende, z.B. sensor.flur_temperatur -> flur"""
    return sensor.replace("sensor.", "").replace(f"_{typ}", "").replace("_", " ")
 
 
def _iso_woche(dt: datetime) -> tuple:
    """gibt (Jahr, Kalenderwoche) zurück"""
    jahr, woche, _ = dt.isocalendar()
    return jahr, woche
 
 
def _wochenbereich(jahr: int, woche: int) -> tuple:
    """gibt Start (Montag 00:00) und Ende (Start + 7 Tage) einer Kalenderwoche zurück"""
    montag = date.fromisocalendar(jahr, woche, 1)
    start = datetime.combine(montag, datetime.min.time())
    return start, start + timedelta(days=7)
 
 
def _tage_unter_schwelle(sensor_daten: dict, start: datetime, ende: datetime) -> set:
    """findet alle Tage, an denen ein Sensor (außer Schlafzimmer) unter den Schwellenwert fällt"""
    tage = set()
    for sensor, punkte in sensor_daten.items():
        if any(a in sensor.lower() for a in AUSGESCHLOSSENE_SENSOREN):
            continue
        for z, w in punkte:
            if start <= z < ende and w < SCHWELLENWERT_TEMP:
                tage.add(z.date())
    return tage
 
 
def _markiere_tage(ax, start: datetime, ende: datetime, heizluefter_tage: set, unter_tage: set) -> None:
    """malt roten Balken über den ganzen Tag - Heizlüfter-Tage zusätzlich mit Beschriftung"""
    trans = ax.get_xaxis_transform()
    for offset in range(7):
        tag = (start + timedelta(days=offset)).date()
        tag_start = datetime.combine(tag, datetime.min.time())
        if tag in heizluefter_tage:
            ax.axvspan(tag_start, tag_start + timedelta(days=1), color="red", alpha=0.25, linewidth=0)
            ax.text(tag_start + timedelta(hours=12), 0.95, "Heizlüfter", transform=trans,
                    rotation=90, rotation_mode="anchor", ha="center", va="top", fontsize=7,
                    color="red", clip_on=True)
        elif tag in unter_tage:
            ax.axvspan(tag_start, tag_start + timedelta(days=1), color="red", alpha=0.25, linewidth=0)
 
 
def _zeichne_diagramm(ax, typ: str, sensor_daten: dict, start: datetime, ende: datetime,
                       heizluefter_tage: set) -> None:
    """zeichnet ein Wochendiagramm - bei Temperatur mit Schwellenwert-Linie und Tag-Markierung"""
    for sensor, punkte in sensor_daten.items():
        zeiten = [z for z, _ in punkte if start <= z < ende]
        werte = [w for z, w in punkte if start <= z < ende]
        if not zeiten:
            continue
        ax.plot(zeiten, werte, marker="o", markersize=2, linewidth=1, label=_sensor_label(sensor, typ))
 
    if typ == "temperatur":
        ax.axhline(SCHWELLENWERT_TEMP, color="red", linestyle="--", linewidth=1,
                   label=f"{SCHWELLENWERT_TEMP:.0f} °C")
        unter_tage = _tage_unter_schwelle(sensor_daten, start, ende)
        _markiere_tage(ax, start, ende, heizluefter_tage, unter_tage)
 
    ax.set_xlim(start, ende)
    ax.xaxis.set_major_locator(mdates.DayLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%a %d.%m."))
    ax.xaxis.set_minor_locator(mdates.HourLocator(byhour=(0, 6, 12, 18)))
    ax.grid(True, which="major", axis="x", alpha=0.4)
    ax.grid(True, which="minor", axis="x", linestyle=":", alpha=0.2)
    ax.grid(True, which="major", axis="y", linestyle=":", alpha=0.3)
 
    einheit = "%" if typ == "luftfeuchtigkeit" else "°C"
    ax.set_ylabel(f"{typ.capitalize()} [{einheit}]")
    ax.set_title(f"Woche ab {start.date():%d.%m.%Y}")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=4, fontsize=8)
 
 
def _text_zeilen(text: str, breite: int = 100) -> list:
    """bricht Text in lesbare Zeilen um, behält vorhandene Zeilenumbrüche"""
    zeilen = []
    for teil in (text or "").splitlines() or [""]:
        zeilen.extend(textwrap.wrap(teil, width=breite) or [""])
    return zeilen
 
 
def _zusammenfassung_bloecke(meta: dict) -> list:
    """baut Liste aus (Text, Zeilenhöhe, Schrift-Optionen) für die Zusammenfassungsseite"""
    bloecke = [("Zusammenfassung", 0.05, dict(fontsize=16, fontweight="bold"))]
 
    kontext = (f"Datei: {meta.get('dateiname', '-')}   |   Sensoren: {meta.get('sensorzahl', '-')}"
               f"   |   Beginn: {meta.get('starttag', '-')}")
    bloecke.append((kontext, 0.06, dict(fontsize=9, color="grey")))
 
    bloecke.append(("Auswertung", 0.04, dict(fontsize=12, fontweight="bold")))
    bloecke += [(z, 0.032, dict(fontsize=10)) for z in _text_zeilen(meta.get("auswertung", ""))]
    bloecke.append(("", 0.03, {}))
 
    bloecke.append(("Report", 0.04, dict(fontsize=12, fontweight="bold")))
    bloecke += [(z, 0.032, dict(fontsize=10)) for z in _text_zeilen(meta.get("report", ""))]
 
    return bloecke
 
 
def _neue_textseite():
    """erstellt eine leere Seite ohne Achsen für Text"""
    fig, ax = plt.subplots(figsize=(11, 8.5))
    ax.axis("off")
    return fig, ax
 
 
def _seite_zusammenfassung(pdf, meta: dict) -> None:
    """schreibt Zusammenfassung ans PDF-Ende, über so viele Seiten wie nötig"""
    fig, ax = _neue_textseite()
    y = 0.95
    unterer_rand = 0.05
 
    for text, hoehe, kwargs in _zusammenfassung_bloecke(meta):
        if y - hoehe < unterer_rand:
            pdf.savefig(fig)
            plt.close(fig)
            fig, ax = _neue_textseite()
            y = 0.95
        if text:
            ax.text(0.03, y, text, transform=ax.transAxes, **kwargs)
        y -= hoehe
 
    pdf.savefig(fig)
    plt.close(fig)
 
 
def erstelle_wochenauswertung(data: dict, ausgabedatei: str = "wochenauswertung.pdf") -> None:
    """Hauptfunktion: baut aus dem Daten-dict die komplette Wochen-PDF"""
    daten = _lade_daten(data)
    meta = data.get("meta", {})
    heizluefter_tage = {datetime.strptime(t, "%Y-%m-%d").date() for t in meta.get("heizlüfter", [])}
 
    alle_zeiten = [z for typ in daten for punkte in daten[typ].values() for z, _ in punkte]
    if not alle_zeiten:
        raise ValueError("Keine Messdaten im übergebenen dict gefunden.")
 
    wochen = sorted({_iso_woche(z) for z in alle_zeiten})
 
    with PdfPages(ausgabedatei) as pdf:
        for typ in ("temperatur", "luftfeuchtigkeit"):
            for jahr, woche in wochen:
                start, ende = _wochenbereich(jahr, woche)
                fig, ax = plt.subplots(figsize=(11, 5))
                _zeichne_diagramm(ax, typ, daten[typ], start, ende, heizluefter_tage)
                pdf.savefig(fig, bbox_inches="tight")
                plt.close(fig)
 
        _seite_zusammenfassung(pdf, meta)
 
    print(f"PDF geschrieben: {ausgabedatei}")