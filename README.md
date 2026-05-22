# FreeCAD Folder Watch Python Agent

Lokale Bridge zwischen einem Coding-Agenten und FreeCAD. FreeCAD führt einmalig ein Macro aus, beobachtet den `inbox/`-Ordner, führt eingereichte Python-Jobs aus, rendert Screenshots und legt Ergebnisse strukturiert unter `out/` ab.

Der Mensch startet FreeCAD und das Macro. Der Agent schreibt danach Modell-Scripts, reicht Jobs ein, liest `result.json` und Screenshots und iteriert.

## Struktur

```text
folder-watch-py-agent/
  freecad_folder_watch_agent.FCMacro  # FreeCAD-seitiger Folder-Watcher
  agent_submit.py                     # schreibt Jobs nach inbox/
  agent_data.py                       # listet und räumt Output-Daten auf
  AGENTS.md                           # operative Anleitung für Agents
  examples/                           # getrackte Beispielmodelle
  models/                             # lokale Modell-Scripts, git-ignored
  inbox/                              # Job-Eingang
  out/                                # Ergebnisse pro Projekt/Session
  logs/                               # Macro-Log
```

## Installation

Alle Befehle werden aus dem Repository-Ordner ausgeführt.

```bash
python3 install_macro_symlink.py
```

Dann FreeCAD öffnen und das Macro starten:

```text
Macro > Macros... > freecad_folder_watch_agent.FCMacro > Execute
```

FreeCAD muss offen bleiben. Nach Änderungen an `freecad_folder_watch_agent.FCMacro` das Macro erneut ausführen.

## Nutzung mit Agents

Agents sollen zuerst `AGENTS.md` lesen. Dort steht das eigentliche Runbook: wann gefragt werden muss, wie Projekt und Session gewählt werden, wann Jobs eingereicht werden dürfen und wie Ergebnisse geprüft werden.

Kurzfassung:

1. Nutzer startet FreeCAD und das Macro.
2. Agent klärt Projektname und Session, zum Beispiel `smart-convert-case` und `default` oder `exploded`.
3. Agent legt lokale Modell-Scripts unter `models/` ab.
4. Agent reicht Jobs mit `agent_submit.py` ein.
5. Agent liest den aktuellen Stand unter `out/projects/<project>/sessions/<session>/current/`.

Beispiel:

```bash
python3 agent_submit.py models/model.py \
  --project smart-convert-case \
  --session default \
  --title first-pass \
  --step
```

Wichtige Outputs:

```text
out/projects/<project>/sessions/<session>/current/result.json
out/projects/<project>/sessions/<session>/current/views/iso.png
out/projects/<project>/sessions/<session>/runs/
```

## Sessions und Projekte

Ein Projekt ist das übergeordnete Modell oder Vorhaben. Eine Session ist eine Ansicht, Variante oder Arbeitsrichtung innerhalb dieses Projekts.

Beispiele:

```text
project: smart-convert-case
sessions:
  default   # zusammengebautes Modell
  exploded  # Exploded View
```

Jobs in derselben Projekt/Session-Kombination verwenden dasselbe FreeCAD-Agent-Dokument wieder. Andere Sessions bleiben getrennt.

## Datenmanagement

```bash
python3 agent_data.py list
python3 agent_data.py stats
```

Aufräumen ist standardmäßig ein Dry-run:

```bash
python3 agent_data.py prune --project smart-convert-case --session default --keep-runs 20
python3 agent_data.py compact --older-than 14d --keep-runs 10
```

Erst mit `--apply` wird gelöscht:

```bash
python3 agent_data.py prune --project smart-convert-case --session default --keep-runs 20 --apply
```

## Wichtige Optionen

- `--project NAME`: Projektordner und Teil der FreeCAD-Session-Identität.
- `--session NAME`: wiederverwendete Session innerhalb eines Projekts.
- `--mode rebuild|update`: `rebuild` baut neu auf, `update` behält vorhandene Objekte.
- `--views iso,front,right,top,bottom`: zu rendernde Screenshots.
- `--param KEY=VALUE`: Parameter an das Modell-Script übergeben.
- `--params-file PATH`: Parameter als JSON-Datei übergeben.
- `--step`: zusätzlich STEP exportieren.
- `--stl`: zusätzlich STL exportieren.
- `--no-fcstd`: keine FreeCAD-Datei speichern.

Lokale, konkrete Projektmodelle gehören nach `models/`; dieser Ordner ist absichtlich nicht getrackt. Getrackte, allgemein nützliche Beispiele gehören nach `examples/`.
