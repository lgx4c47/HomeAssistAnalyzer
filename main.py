import glob
import drawer_lite
from datetime import datetime, timedelta

MIETE = 764.67
TEMPERATUR_SCHWELLWERT = 20

'''Aufrufen anschließend öffnen aus raw, einteilen in sinnvolles Format, ausrechnen der Minderungsfähigen Tage, Report zu durchgeführten Änderungen erstellen'''

def load_call():
    '''Durchsucht raw und startet die Analyze für alle Dateien'''
    for datei in glob.glob('./raw/*'):
        #try:
            analyze(datei)
        #except:
            #print(f"Analyse von \"{datei}\" nicht möglich")

def analyze (file:str):
    '''Erstellt Strukturierte Datendarstellung in Dictionary (Beispiel): {"sensor1":{"messwert":[MESSWERTE], "zeit":[ZEITEN]}, "sensor2":{...},...}
        
        Bei mehreren Sensoren werden diese also separat gespeichert (eigene Zeiterfassung).'''
    sorted_data={"temperatur":{}, "luftfeuchtigkeit":{}}
    report = f"Datei {file} wird analysiert"
    sensorcount = 0
    starttag = datetime.strptime("2150-06-06", "%Y-%m-%d").date()

    with open(file) as rawfile: 
        linecount = 0
        useless_lines = []
        for line in rawfile:
            arr = line.split(",")
            # prüfen ob temperatur oder feuchtigkeit
            try:
                kind = arr[0].split('_')[arr[0].count('_')]
            except:
                useless_lines.append(linecount)
                kind = ""
                continue
            # Datumsformat anpassen
            zeit =  arr[2].replace("T", " ").replace("Z\n", "")
            if kind == "temperatur" or kind == "luftfeuchtigkeit":
                try:
                    # Sensor bereits im Datensatz?
                    if arr[0] in sorted_data[kind]:
                        sorted_data[kind][arr[0]]["messwert"].append(arr[1])
                        sorted_data[kind][arr[0]]["zeit"].append(zeit)   
                    else: 
                        sorted_data[kind][arr[0]] = {"messwert":[arr[1]], "zeit":[zeit]}
                        sensorcount += 1
                        starttag = erster(datetime.strptime(zeit[:10], "%Y-%m-%d").date(), starttag)
                except: 
                    report += f"\n Error in Zeile {linecount}"
            else: 
                # unverwertbare Zeilen speichern
                useless_lines.append(linecount)
            linecount += 1
    
    report += f"\n\n Alle {linecount} Zeilen analysiert und in sorted_data_temp eingefügt. {len(useless_lines)} enthielten keine verwertbaren Daten (z.B. Überschriften/ Batteriestatus)\nDatei {file} abgeschlossen\n\nZeilen ohne verwertbare Information: {useless_lines}\n\n"

    sorted_data["meta"] = {
            "sensorzahl":sensorcount // 2, 
            "starttag":starttag,
            "dateiname":file.replace("/", "").replace("\\", "").replace(".", "-").replace(" ", "_"),
            "report":report,
            }
    sorted_data["meta"]["auswertung"] = auswertung(sorted_data)
    sorted_data = teile_wochen(sorted_data)
    drawer_lite.erstelle_wochenauswertung(sorted_data, f"./auswertung/Auswertung_{sorted_data["meta"]["dateiname"]}.pdf")
        

def teile_wochen(data:dict):
    '''teilt in Wochen ein'''
    startwoche = 1
    weekwise={"luftfeuchtigkeit":{startwoche:{}}, "temperatur":{startwoche:{}}}
    starttag = data["meta"]["starttag"]
    # iter über einzelne sensoren
    kinds = ["luftfeuchtigkeit", "temperatur"]
    for kind in kinds: 
        woche = 1
        for sensor in data[kind]:
            for i in range(len(data[kind][sensor]["messwert"])):
                if (datetime.strptime(data[kind][sensor]["zeit"][i][:10].strip(), "%Y-%m-%d").date() - starttag).days <= 7:
                    if sensor not in weekwise[kind][woche]: weekwise[kind][woche][sensor] = {"messwert":[], "zeit":[]}
                    weekwise[kind][woche][sensor]["messwert"].append(data[kind][sensor]["messwert"][i])
                    weekwise[kind][woche][sensor]["zeit"].append(data[kind][sensor]["zeit"][i])
                else:
                    wochen = (datetime.strptime(data[kind][sensor]["zeit"][i][:10].strip(), "%Y-%m-%d").date() - starttag).days // 7
                    woche += wochen
                    starttag += timedelta(weeks=wochen)
                    if woche in weekwise[kind]: 
                        weekwise[kind][woche][sensor] = {"messwert":data[kind][sensor]["messwert"],"zeit":data[kind][sensor]["zeit"]}
                    else: 
                        weekwise[kind][woche] = {sensor: {"messwert":[data[kind][sensor]["messwert"][i]],"zeit":[data[kind][sensor]["zeit"][i]]}}
    weekwise["meta"] = data["meta"]
    return weekwise


def erster(tag1, tag2):
    '''gibt den früheren Tag zurück'''
    if (tag1 - tag2).days < 0:
        return tag1
    return tag2

def auswertung(data):
    auswertung = ""
    for sensor in data["temperatur"]:
        tage25 = []
        tage50 = []
        tage75 = []
        tage100 = []
        count_tage25 = count_tage50 = count_tage75 = count_tage100 = 0
        tage_gesamt = 0
        tag = data["meta"]["starttag"]
        tagesliste = {}
        for i in range(len(data["temperatur"][sensor]["messwert"])):
            temp, zeit = data["temperatur"][sensor]["messwert"][i], data["temperatur"][sensor]["zeit"][i]
            # Tag bereits erfasst?
            if zeit[:10] == tag:
                # Stunde bereits erfasst? (gerechnet wird hier Stundendurchschnitt)
                if zeit[11-12] in tagesliste:
                    tagesliste[zeit[11-12]].append(temp) 
                else:
                    tagesliste[zeit[11-12]] = [temp]
            else:
                tmp = tagesauswertung(tagesliste)
                if tmp >= 20: 
                    tage25.append(tag)
                    count_tage25 += 1
                elif tmp >= 50:
                    tage50.append(tag)
                    count_tage50 +=1
                elif tmp >= 75: 
                    tage75.append(tag)
                    count_tage75 +=1
                elif tmp >= 100: 
                    tage100.append(tag)
                    count_tage100 +=1
                tag = zeit[:10]
        auswertung += f"Sensor: {sensor}: \n"
        '''auswertung += f"An insgesamt {count_tage100} wurden in 100% der aufgezeichneten Stunden durchschnittlich unter 20°C gemessen. \nBetroffene Tage: {tage100}"
        auswertung += f"An insgesamt {count_tage75} wurden in 75% der aufgezeichneten Stunden durchschnittlich unter 20°C gemessen. \nBetroffene Tage: {tage75}"
        auswertung += f"An insgesamt {count_tage50} wurden in 50% der aufgezeichneten Stunden durchschnittlich unter 20°C gemessen. \nBetroffene Tage: {tage50}\n\n"'''
        auswertung += f"An insgesamt {count_tage25} Tagen wurden in 20% der aufgezeichneten Stunden durchschnittlich unter 20°C gemessen. Das entspräche {len(tage25)*MIETE/30*0.2} € Mietminderung (bei 20%)\nBetroffene Tage: {tage25}\n\n"
    return auswertung

def tagesauswertung(tagesliste):
    'Temperaturunterschreitungen berechnen (prozent der Stundenweisen Durchschnittswerte)'
    stundendurchschnitte = []
    tmp = 0
    count = 0
    for stunde in tagesliste:
        for temp in tagesliste[stunde]: tmp += float(temp)
        count += 1
        tmp = tmp / len(tagesliste[stunde])
        stundendurchschnitte.append(tmp)
    for stunde in stundendurchschnitte: 
        if stunde <= TEMPERATUR_SCHWELLWERT: tmp += 100 / count
    return tmp
    


if __name__=='__main__':
    load_call()
