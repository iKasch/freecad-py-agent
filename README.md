# FreeCAD Folder Watch Python Agent

Local bridge between your own coding agent and FreeCAD. FreeCAD runs one macro, watches a workspace `inbox/`, executes submitted Python jobs, and stores structured results under `out/`. Screenshots and exports are opt-in.

This project does not include or run an AI agent inside FreeCAD. Use an external agent that can read and write local files, for example Codex, Claude Code, or a similar coding agent. The human starts FreeCAD and the macro; the external agent works from the generated workspace, writes model scripts, submits jobs, reads compact summaries, and iterates. Screenshots are for deliberate visual checkpoints.

## What To Clone

Clone this repository. Do not set this repository as FreeCAD's macro folder.

Run the setup script once. It creates:

- a clean agent workspace, by default `~/FreeCADAgent`
- one FreeCAD macro wrapper, `freecad_agent.FCMacro`

Point your external coding agent at the generated workspace. The workspace contains only the files the agent needs:

```text
FreeCADAgent/
  freecad_folder_watch_agent.FCMacro  # bridge macro source
  agent_submit.py                     # submits jobs to inbox/
  agent_data.py                       # lists and cleans output data
  AGENTS.md                           # operational runbook for agents
  README.md                           # short user documentation
  examples/                           # tracked example models
  models/                             # local model scripts, git-ignored
  inbox/                              # incoming jobs
  out/                                # results by project/session
  logs/                               # macro log
```

## Installation

From the cloned repository:

```bash
python3 setup_freecad_agent.py
```

Then open FreeCAD and run the generated macro:

```text
Macro > Macros... > freecad_agent.FCMacro > Execute
```

Keep FreeCAD open while the agent works. After changing or updating `freecad_folder_watch_agent.FCMacro`, run `freecad_agent.FCMacro` again in FreeCAD so the running bridge reloads the new code.

Custom workspace:

```bash
python3 setup_freecad_agent.py --workspace /path/to/FreeCADAgent
```

## Agent Usage

Open your external coding agent in the generated workspace, or tell it that this workspace is the working directory for the FreeCAD bridge. Then tell it to read `AGENTS.md` first. That file is the operational runbook: when to ask the user, how to choose project/session names, when jobs may be submitted, and how results should be checked.

Short flow:

1. User starts FreeCAD and runs `freecad_agent.FCMacro`.
2. User starts their own file-capable coding agent in the generated workspace.
3. Agent establishes a project and session, for example `smart-convert-case` and `default` or `exploded`.
4. Agent stores local model scripts under `models/`.
5. Agent submits jobs with `agent_submit.py`.
6. Agent reads the current state from `out/projects/<project>/sessions/<session>/current/`.

Example:

```bash
python3 agent_submit.py models/model.py \
  --project smart-convert-case \
  --session default \
  --title first-pass \
  --no-fcstd \
  --quiet
```

Important outputs:

```text
out/projects/<project>/sessions/<session>/current/result.json
out/projects/<project>/sessions/<session>/current/result_summary.json
out/projects/<project>/sessions/<session>/current/views/iso.png  # when screenshots were requested
out/projects/<project>/sessions/<session>/runs/
```

For routine iteration, have the agent inspect the compact summary first:

```bash
python3 agent_data.py show --project smart-convert-case --session default --brief
```

Use screenshots, full `result.json`, and exports when the compact summary is not enough to make the next modeling decision, or when you want a deliberate visual checkpoint.

## Projects And Sessions

A project is the overall model or task. A session is one view, variant, or work direction inside that project.

Example:

```text
project: smart-convert-case
sessions:
  default   # assembled model
  exploded  # exploded view
```

Jobs with the same project/session pair reuse the same FreeCAD agent document. Different sessions stay separate.

## Data Management

Inspect stored data:

```bash
python3 agent_data.py list
python3 agent_data.py stats
python3 agent_data.py show --project smart-convert-case --session default --brief
python3 agent_data.py show --project smart-convert-case --session default
```

Cleanup commands are dry-runs by default:

```bash
python3 agent_data.py prune --project smart-convert-case --session default --keep-runs 20
python3 agent_data.py compact --older-than 14d --keep-runs 10
```

Add `--apply` to actually delete files:

```bash
python3 agent_data.py prune --project smart-convert-case --session default --keep-runs 20 --apply
```

## Important Options

- `--project NAME`: project folder and part of the FreeCAD session identity.
- `--session NAME`: reused session inside a project.
- `--mode rebuild|update`: `rebuild` starts fresh, `update` keeps existing objects.
- `--views iso,front,right,top,bottom`: screenshots to render. Defaults to no screenshots; use `--views none` to skip explicitly.
- `--param KEY=VALUE`: pass one parameter to the model script.
- `--params-file PATH`: pass parameters from a JSON file.
- `--step`: export STEP.
- `--stl`: export STL.
- `--3mf`: export 3MF.
- `--no-fcstd`: do not save a FreeCAD file.

For low-cost design iteration, skip screenshots and the `.FCStd` checkpoint:

```bash
python3 agent_submit.py models/model.py \
  --project smart-convert-case \
  --session default \
  --no-fcstd \
  --quiet
```

Request one smaller screenshot only when visual inspection is useful:

```bash
python3 agent_submit.py models/model.py \
  --project smart-convert-case \
  --session default \
  --views iso \
  --width 900 \
  --height 700 \
  --no-fcstd \
  --quiet
```

Run a full checkpoint with multiple views and exports before user review, handoff, or manufacturing export.

Concrete local project models belong in `models/`; this folder is intentionally not tracked. Tracked, generally useful examples belong in `examples/`.
