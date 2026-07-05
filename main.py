import csv
import glob
from datetime import date

'''Aufrufen anschließend öffnen aus raw, einteilen in sinnvolles Format, ausrechnen der Minderungsfähigen Tage, Report zu durchgeführten Änderungen erstellen'''

def load_call():
    '''Durchsucht raw und startet die Analyze für alle Dateien'''
    for datei in glob.glob('./raw/*'):
        #try:
            analyze(datei)
      #  except:
          #  print(f"Analyse von \"{datei}\" nicht möglich")

def analyze (file:str):
    '''Erstellt Strukturierte Datendarstellung in Dictionary (Beispiel): {"sensor1":{[{"temperatur"="11.0", "zeit"="2026-07-01 05:15:59"}, 
        {"temperatur"="12.0", "zeit"="2026-07-03 05:15:59"},...], "sensor2":[{...}]}
        
        Bei mehreren Sensoren werden diese also separat gespeichert (eigene Zeiterfassung).'''
    sorted_data_temp={}
    sorted_data_feuchtigkeit={}
    report = f"Datei {file} wird analysiert"
    sensorcount = 0
    with open(file) as rawfile: 
        linecount = 0
        useless_lines = []
        for line in rawfile:
            arr = line.split(",")
            kind = ""
            try:
                kind = arr[0].split('_')[arr[0].count('_')]
            except:
                useless_lines.append(linecount)
                continue
            datetime =  arr[2].replace("T", " ").replace("Z\n", "")
            if kind == "temperatur":
                try:
                    if arr[0] in sorted_data_temp:
                        sorted_data_temp[arr[0]].append({"messwert":arr[1], "zeit":datetime})  
                    else: 
                        sorted_data_temp[arr[0]]=[{"messwert":arr[1], "zeit":datetime}]
                        sensorcount += 1
                except: 
                    report += f"\n Error in Zeile {linecount}"
            elif kind == "luftfeuchtigkeit":
                try:
                    if arr[0] in sorted_data_feuchtigkeit:
                        sorted_data_feuchtigkeit[arr[0]].append({"messwert":arr[1], "zeit":datetime})   
                    else: sorted_data_feuchtigkeit[arr[0]]=[{"messwert":arr[1], "zeit":datetime}]
                except: 
                    report += f"\n Error in Zeile {linecount}"
            else: 
                useless_lines.append(linecount)
            linecount += 1
    sorted_data_feuchtigkeit["sensorzahl"] = sensorcount
    sorted_data_temperatur["sensorzahl"] = sensorcount
    report += f"\n\n Alle {linecount} Zeilen analysiert und in sorted_data_temp eingefügt. {len(useless_lines)} enthielten keine verwertbaren Daten (z.B. Überschriften/ Batteriestatus)\nDatei {file} abgeschlossen\n\nZeilen ohne verwertbare Information: {useless_lines}"
    secure_filename = file.replace("/", "").replace("\\", "").replace(".", "")
    unify_data(sorted_data_temp)
    unify_data(sorted_data_feuchtigkeit)
    #to_csv(sorted_data_temp, f"./analyzed/sorted_data_temperatur_{secure_filename}.csv")
    #to_csv(sorted_data_feuchtigkeit, f"./analyzed/sorted_data_feuchtigkeit_{secure_filename}.csv")
    print(teile_wochen_tage(sorted_data_temp))
    #make_report(report, secure_filename)

def unify_data(data:dict):
    '''Rechnet durchschnitt in 1-Min-Blöcken und Teilt sensoren gemeinsame Zeitleiste zu'''
    unified_data = {}
    count = 0
    for sensor in data:
        for messwert in sensor:
            if messwert["zeit"][:16] in unified_data:
                unified_data[messwert["zeit"][:16]][count].append(messwert["messwert"])
            else: 
                unified_data[messwert["zeit"][:16]] = [""] * data["sensorzahl"]
                unified_data[messwert["zeit"][:16]][count] = [messwert["messwert"]]
        '''Werte normalisieren'''
        for arr in unified_data:
            if arr[count] == "":
                continue
            else:
                arr[count] = avg_array(arr[count])
        count += 1

def avg_array(arr):
    '''Durchschnitt aus array'''
    sum = 0
    try:
        for i in arr:
            sum += float(i)
        return sum/len(arr)
    except:
        return ""
        

def teile_wochen_tage(data:dict):
    '''teilt in Wochen und Tage ein'''
    woche_tag={}
    sensorcount = 0
    for sensor in data:
        sensorcount += 1
        woche = 1
        wochencounter = 0
        woche_tag_sensor={1:{}}
        for messwert in data[sensor]:
            if messwert["datum"] in woche_tag_sensor[woche]:
                woche_tag_sensor[woche][messwert["datum"]].append({messwert["zeit"]:messwert["messwert"]})
            else:
                if wochencounter ==7:
                    woche += 1
                    wochencounter = 0
                    woche_tag_sensor[woche] = {}
                woche_tag_sensor[woche][messwert["datum"]] = [{messwert["zeit"]:messwert["messwert"]}]
                wochencounter += 1
        for woche in woche_tag_sensor:
            if woche not in woche_tag:
                    woche_tag[woche] = {}
            for tag in woche_tag_sensor[woche]:
                if tag in woche_tag[woche]:
                    woche_tag[woche][tag][sensor] = woche_tag_sensor[woche][tag]
                else:
                    woche_tag[woche] = {tag:{sensor:woche_tag_sensor[woche][tag]}}
    woche_tag["sensorzahl"] = sensorcount
    return woche_tag

def to_csv(data:dict, name:str):
    '''Überführt sorted_data in CSV'''
    lines=["", "", ""]
    for sensor in data:
        '''Initialisiert pro Sensor, anschließend werden jeweils die Zeilen bearbeitet (umsetzung als Array --> Flexibel)'''
        lines[0] += f"{sensor};;;"
        lines[1] += "Datum;Uhrzeit;Messwert;"
        for i in range(len(data[sensor])):
            try:
                lines[2+i] += f"{data[sensor][i]['datum']};{data[sensor][i-1]['zeit']};{data[sensor][i-1]['messwert']};"
            except:
                try:
                    lines.append(f"{data[sensor][i]['datum']};{data[sensor][i-1]['zeit']};{data[sensor][i-1]['messwert']};")
                except:
                    try:
                        lines[2+i]=";;;"
                    except:
                        lines.append(";;;")
    with open(name,"w", newline="", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")

def to_csv_weekwise(data:dict, name:str):
    '''Überführt wochen- und tageweise geordnete daten in CSV'''
    lines=["", "", ""]
    for woche in data:
        '''Initialisiert pro Sensor, anschließend werden jeweils die Zeilen bearbeitet (umsetzung als Array --> Flexibel)'''
        lines[0] += f"{woche}"
        lines[2] += "Datum;Uhrzeit;Messwert;"
        for i in range(len(data[sensor])):
            try:
                lines[2+i] += f"{data[sensor][i]['datum']};{data[sensor][i-1]['zeit']};{data[sensor][i-1]['messwert']};"
            except:
                try:
                    lines.append(f"{data[sensor][i]['datum']};{data[sensor][i-1]['zeit']};{data[sensor][i-1]['messwert']};")
                except:
                    try:
                        lines[2+i]=";;;"
                    except:
                        lines.append(";;;")
    with open(name,"w", newline="", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")

def make_report(report: str, name: str):
    with open(f"report_{name}.txt", "a") as f:
        f.write(report)

if __name__=='__main__':
    load_call()
