# FreeCAD Folder Watch Python Agent

Kleine lokale Bridge zwischen einem Coding-Agenten und FreeCAD. FreeCAD fuehrt eine einmal gestartete Macro aus, beobachtet `inbox/`, laedt Python-Jobs in ein wiederverwendetes Agent-Session-Dokument, rendert Screenshots aus der GUI und legt Ergebnisse in `out/` ab.

## Struktur

```text
folder-watch-py-agent/
  freecad_folder_watch_agent.FCMacro  # einmal in FreeCAD starten
  agent_submit.py                     # schreibt Jobs nach inbox/
  examples/perforated_plate.py        # Beispielmodell
  inbox/                              # Job-Eingang
  out/                                # Ergebnisse pro Job
  logs/                               # Macro-Log
```

## Einmal in FreeCAD starten

Option A, bequem ueber FreeCADs Macro-Menue:

```bash
cd /Users/kim.schneider/Development/private/freecad/macros/folder-watch-py-agent
python3 install_macro_symlink.py
```

Danach FreeCAD GUI oeffnen und `Macro > Macros... > freecad_folder_watch_agent.FCMacro > Execute` waehlen.

Option B, ohne Installation, einmal in der FreeCAD Python Console ausfuehren:

```text
exec(open("/Users/kim.schneider/Development/private/freecad/macros/folder-watch-py-agent/freecad_folder_watch_agent.FCMacro", encoding="utf-8").read())
```

Die Macro laeuft danach per `QTimer` weiter, solange FreeCAD offen ist. Ein erneutes Ausfuehren startet sie sauber neu.

## Job einreichen

Aus einem Terminal:

```bash
cd /Users/kim.schneider/Development/private/freecad/macros/folder-watch-py-agent
python3 agent_submit.py examples/perforated_plate.py --step
```

FreeCAD verarbeitet den Job automatisch. Das Ergebnis liegt danach unter:

```text
out/<job-id>/
  result.json
  <output>.FCStd
  <output>.step      # wenn --step gesetzt wurde
  views/iso.png
  views/front.png
  views/right.png
  views/top.png
```

`out/latest_result.json` zeigt immer auf den zuletzt verarbeiteten Jobstatus.

## Parametrische Iteration

Variante B bedeutet hier: Das Modell-Script liest stabile Parameter aus `PARAMS`, baut daraus reproduzierbar dieselben stabil benannten Objekte und wird in derselben Agent-Session neu berechnet. Dadurch veraendert der Agent nicht manuell beliebige FreeCAD-History, sondern iteriert ueber explizite Parameter.

Einzelne Parameter direkt uebergeben:

```bash
python3 agent_submit.py examples/parametric_mounting_plate.py \
  --session default \
  --title parametric-plate-wide \
  --param plate_width=150 \
  --param hole_count=5 \
  --param hole_diameter=11 \
  --step
```

Oder Parameter als JSON-Datei:

```json
{
  "plate_width": 150,
  "plate_depth": 70,
  "hole_count": 5,
  "rail_height": 16
}
```

```bash
python3 agent_submit.py examples/parametric_mounting_plate.py \
  --session default \
  --params-file params.json \
  --step
```

Im Modell-Script stehen die Werte als `PARAMS` bereit:

```python
params = {"plate_width": 110, **PARAMS}
```

## Workflow fuer Agenten

1. Modell-Script als normale FreeCAD-Python-Datei schreiben, zum Beispiel `model.py`.
2. Sicherstellen, dass die FreeCAD-GUI offen ist und `freecad_folder_watch_agent.FCMacro` laeuft.
3. Job in die wiederverwendete Agent-Session einreichen:

```bash
cd /Users/kim.schneider/Development/private/freecad/macros/folder-watch-py-agent
python3 agent_submit.py /abs/path/to/model.py --session default --title my-model --step
```

4. Auf das Ergebnis warten und `out/latest_result.json` lesen.
5. Bei `status: "ok"` die Screenshots unter `out/<job-id>/views/` ansehen.
6. Bei `status: "error"` `error` und `traceback` aus `result.json` verwenden.
7. Modell-Script anpassen und erneut mit `agent_submit.py` einreichen.

Fuer visuelle Iteration ist meistens `views/iso.png` der erste Check. Fuer technische Kontrolle liefert `result.json` zusaetzlich Objektliste, Bounding Boxes, Flaechen und Volumina.

Standardmaessig verwendet jeder Job die Session `default`. FreeCAD erstellt dafuer einmal ein Dokument mit dem sichtbaren Label `Agent default`; weitere Jobs in derselben Session leeren nur dieses Agent-Dokument und befuellen es neu. Bereits offene Nicht-Agent-Dokumente bleiben offen und unveraendert.

Mehrere parallele Entwuerfe laufen ueber verschiedene Sessions:

```bash
python3 agent_submit.py model.py --session desk-organizer
python3 agent_submit.py model.py --session lamp-concept
```

Nur mit `--use-active-document` wird absichtlich in das aktuell aktive FreeCAD-Dokument geschrieben. Nur mit `--new-document` wird fuer jeden Job ein frisches neues Dokument erstellt.

Wichtig: Nach Updates an `freecad_folder_watch_agent.FCMacro` die Macro in FreeCAD erneut ausfuehren. In `result.json` sollte `agent_version` stehen; fuer wiederverwendete Session-Dokumente mindestens `0.3.0-session-document`, fuer stabile Screenshots nach Session-Updates mindestens `0.3.1-session-view-refresh`, fuer stabile sichtbare Session-Namen mindestens `0.3.4-enforce-label-after-save`.

## Modell-Scripts

Ein Job-Script ist normales FreeCAD-Python. Die Macro stellt diese Variablen bereit:

```python
App      # FreeCAD module
Gui      # FreeCADGui module, wenn in der GUI verfuegbar
DOC      # aktives Dokument
JOB      # Job-Dictionary aus der JSON-Datei
OUT_DIR  # Ausgabeordner fuer diesen Job
PARAMS   # Parameter-Dictionary aus --param und --params-file
```

Minimalbeispiel:

```python
import Part

box = DOC.addObject("Part::Feature", "box")
box.Shape = Part.makeBox(20, 20, 10)
DOC.recompute()
```

## Optionen

```bash
python3 agent_submit.py model.py \
  --session desk-organizer \
  --title desk-organizer \
  --views iso,front,right,top \
  --width 1600 \
  --height 1200 \
  --step \
  --stl
```

Wichtige Flags:

- `--session NAME`: wiederverwendetes Agent-Dokument fuer iterative Arbeit, Default `default`.
- `--use-active-document`: absichtlich in das aktuell aktive FreeCAD-Dokument schreiben.
- `--new-document`: fuer diesen Job ein frisches neues Dokument erstellen.
- `--restore-active-document`: nach Screenshot/Export zum vorher aktiven FreeCAD-Dokument zurueckwechseln.
- `--params-file PATH`: JSON-Datei mit Parametern fuer das Script.
- `--param KEY=VALUE`: einzelnen Parameter setzen oder ueberschreiben; `VALUE` wird als JSON geparst, wenn moeglich.
- `--step`: zusaetzlich STEP exportieren.
- `--stl`: zusaetzlich STL exportieren.
- `--no-fcstd`: keine `.FCStd` speichern.

## Sicherheitsmodell

Diese Bridge fuehrt lokale Python-Scripts in FreeCAD aus. Das ist absichtlich maechtig und sollte nur mit einem festen lokalen Ordner benutzt werden. Keine fremden Scripts in `inbox/` legen.

## Stoppen

In der FreeCAD Python Console:

```python
App._folder_watch_agent.stop()
```

Zum Starten die Macro erneut ausfuehren.
