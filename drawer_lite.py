from datetime import date, datetime, timedelta

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_pdf import PdfPages


TEMP_HAUPT = 20
TEMP_OBEN = 21
TEMP_UNTEN = 18

# DIN A4 quer in Zoll
A4_QUER = (11.69, 8.27)


def _wochenbereich(jahr: int, woche: int):
    """Gibt Montag 00:00 bis zum folgenden Montag zurück."""
    montag = date.fromisocalendar(jahr, woche, 1)
    start = datetime.combine(montag, datetime.min.time())
    return start, start + timedelta(days=7)


def _wochen(data: dict, typ: str):
    """Ermittelt alle Kalenderwochen einer Messart."""
    return sorted({
        zeit.isocalendar()[:2]
        for zeit, _, messart, _ in data["messungen"]
        if messart == typ
    })


def _sensoren(data: dict, typ: str):
    """Gibt alle Sensoren einer Messart zurück."""
    return sorted({
        sensor
        for _, sensor, messart, _ in data["messungen"]
        if messart == typ
    })


def _punkte(
    data: dict,
    typ: str,
    sensor: str,
    start: datetime,
    ende: datetime,
):
    """Filtert Messpunkte nach Messart, Sensor und Zeitraum."""
    return sorted([
        (zeit, wert)
        for zeit, sensorname, messart, wert in data["messungen"]
        if (
            messart == typ
            and sensorname == sensor
            and start <= zeit < ende
        )
    ])


def _schwellen(ax):
    """Zeichnet die drei Temperatur-Orientierungswerte."""
    ax.axhline(
        TEMP_HAUPT,
        color="red",
        linestyle="--",
        linewidth=1.5,
        label="20 °C",
    )

    ax.axhline(
        TEMP_OBEN,
        color="gray",
        linestyle=":",
        linewidth=1,
        alpha=0.7,
        label="21 °C",
    )

    ax.axhline(
        TEMP_UNTEN,
        color="gray",
        linestyle=":",
        linewidth=1,
        alpha=0.7,
        label="18 °C",
    )


def _diagramm(
    ax,
    data: dict,
    typ: str,
    start: datetime,
    ende: datetime,
):
    """Zeichnet alle Sensoren einer Messart für eine Kalenderwoche."""
    for sensor in _sensoren(data, typ):
        punkte = _punkte(data, typ, sensor, start, ende)

        if not punkte:
            continue

        zeiten, werte = zip(*punkte)

        ax.plot(
            zeiten,
            werte,
            linewidth=1,
            marker="o",
            markersize=2,
            label=sensor.replace("_", " "),
        )

    if typ == "temperatur":
        _schwellen(ax)

    ax.set_xlim(start, ende)

    ax.xaxis.set_major_locator(mdates.DayLocator())
    ax.xaxis.set_major_formatter(
        mdates.DateFormatter("%a\n%d.%m.")
    )

    ax.xaxis.set_minor_locator(
        mdates.HourLocator(byhour=(6, 12, 18))
    )

    ax.grid(
        axis="x",
        which="major",
        alpha=0.4,
    )

    ax.grid(
        axis="x",
        which="minor",
        linestyle=":",
        alpha=0.2,
    )

    ax.grid(
        axis="y",
        linestyle=":",
        alpha=0.3,
    )

    if typ == "temperatur":
        titel = "Temperatur"
        einheit = "°C"
    else:
        titel = "Luftfeuchtigkeit"
        einheit = "%"

    ax.set_ylabel(einheit)

    ax.set_title(
        f"{titel} – Woche ab {start:%d.%m.%Y}",
        fontsize=13,
    )

    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, -0.12),
        ncol=4,
        fontsize=8,
    )


def _wochenseite(
    pdf,
    data: dict,
    typ: str,
    start: datetime,
    ende: datetime,
):
    """Erstellt eine DIN-A4-Seite mit Diagramm und Notizbereich."""
    fig = plt.figure(figsize=A4_QUER)

    # Diagramm
    ax = fig.add_axes([
        0.08,
        0.35,
        0.88,
        0.55,
    ])

    # Notizbereich
    notizen = fig.add_axes([
        0.08,
        0.07,
        0.88,
        0.16,
    ])

    _diagramm(
        ax,
        data,
        typ,
        start,
        ende,
    )

    notizen.set_xlim(0, 1)
    notizen.set_ylim(0, 1)

    notizen.set_xticks([])
    notizen.set_yticks([])

    notizen.set_title(
        "Notizen",
        loc="left",
        fontsize=10,
        pad=6,
    )

    # Schreiblinien
    for y in (0.75, 0.5, 0.25):
        notizen.axhline(
            y,
            linewidth=0.5,
            color="lightgray",
        )

    pdf.savefig(fig)
    plt.close(fig)


def _reportseite(pdf, meta: dict):
    """Erstellt die technische Abschlussseite."""
    fig = plt.figure(figsize=A4_QUER)

    ax = fig.add_axes([
        0.08,
        0.08,
        0.84,
        0.84,
    ])

    ax.axis("off")

    ax.text(
        0,
        1,
        "Report",
        fontsize=16,
        fontweight="bold",
        va="top",
    )

    text = (
        f"Ausgewertete Datei: {meta.get('datei', '-')}\n\n"
        f"Zeilen insgesamt: {meta.get('zeilen', '-')}\n"
        f"Nicht verwertbare Zeilen: {meta.get('unverwertbar', '-')}"
    )

    ax.text(
        0,
        0.9,
        text,
        fontsize=10,
        va="top",
        linespacing=1.6,
    )

    pdf.savefig(fig)
    plt.close(fig)


def erstelle_wochenauswertung(
    data: dict,
    ausgabedatei: str = "wochenauswertung.pdf",
):
    """Erstellt die vollständige DIN-A4-PDF-Auswertung."""
    if not data.get("messungen"):
        raise ValueError("Keine Messdaten vorhanden.")

    with PdfPages(ausgabedatei) as pdf:

        # Zuerst alle Temperaturseiten,
        # danach alle Luftfeuchtigkeitsseiten.
        for typ in ("temperatur", "luftfeuchtigkeit"):

            for jahr, woche in _wochen(data, typ):
                start, ende = _wochenbereich(jahr, woche)

                _wochenseite(
                    pdf,
                    data,
                    typ,
                    start,
                    ende,
                )

        _reportseite(
            pdf,
            data.get("meta", {}),
        )

    print(f"PDF geschrieben: {ausgabedatei}")