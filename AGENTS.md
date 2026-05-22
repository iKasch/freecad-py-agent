# Agent Instructions

This repository is a local bridge between a coding agent and a running FreeCAD GUI. The human starts FreeCAD and the macro; the agent writes FreeCAD Python scripts, submits jobs, reads screenshots/results, and iterates.

## First Response To A User

When a user asks you to build or modify a FreeCAD model with this repository, first make sure the runtime bridge is available.

Do not submit a FreeCAD job or create test geometry just to verify the bridge. Reading this file, inspecting CLI help, checking folders, and asking the user whether FreeCAD is open are safe readiness checks. Submitting a job changes the user's FreeCAD session and is only allowed after the user asks for a concrete model/change, or after the user explicitly asks you to test the bridge.

Tell the user to do this once in FreeCAD:

1. Open FreeCAD.
2. Run `Macro > Macros... > freecad_folder_watch_agent.FCMacro > Execute`.
3. Keep FreeCAD open while you work.

If the macro is not installed in FreeCAD yet, tell the user to run this from the repository first:

```bash
python3 install_macro_symlink.py
```

Alternatively, they can paste this into the FreeCAD Python console:

```python
exec(open("/absolute/path/to/folder-watch-py-agent/freecad_folder_watch_agent.FCMacro", encoding="utf-8").read())
```

After changes to `freecad_folder_watch_agent.FCMacro`, tell the user to run the macro again in FreeCAD.

## Working Model

Use these files:

- `agent_submit.py`: submit a model script to the running FreeCAD macro.
- `agent_data.py`: inspect and clean output data.
- `freecad_folder_watch_agent.FCMacro`: the FreeCAD-side folder watcher.
- `examples/`: reference model scripts.
- `out/projects/<project>/sessions/<session>/current/`: current output for one project/session.
- `out/projects/<project>/sessions/<session>/runs/`: historical runs for one project/session.

Do not write job files directly into `inbox/`. Use `agent_submit.py`; it copies the script and writes the job JSON atomically.

## Project And Session Choice

Always submit jobs with explicit `--project` and `--session`.

Before the first submit in a conversation, establish the project/session target. If the user has not named a project, ask for a project name. Do not silently use `default` just because it is the CLI default.

Choose names like this:

- `--project`: stable slug for the user's overall task, product, or model family, for example `desk-organizer` or `mounting-bracket`.
- `--session`: stable slug for the current view, design branch, or representation, for example `default`, `exploded`, `concept-a`, or `variant-b`.

Use `agent_data.py list` to inspect existing project/session folders before choosing a target. If the intended project already has sessions, continue the matching session instead of creating or overwriting another one. If the user wants another view of the same model, use the same project and a different session, for example `default` for the assembled model and `exploded` for an exploded view.

Reuse the same project/session while iterating on the same view or design branch. Use a new session for a real alternative or representation that should stay separate. If it is unclear whether the next job should update `default`, `exploded`, or another existing session, ask the user before submitting.

## Normal Job Flow

Run commands from the repository root unless you pass `--root` explicitly.

Only start this flow after the user has described the model/change to build, or has explicitly requested a bridge test.

1. Create or update a normal FreeCAD Python model script.
2. Submit it:

```bash
python3 agent_submit.py /abs/path/to/model.py \
  --project <project> \
  --session <session> \
  --title <short-run-title> \
  --step
```

3. Wait for:

```text
out/projects/<project>/sessions/<session>/current/result.json
```

4. Read `current/result.json`.
5. If `status` is `ok`, inspect `current/views/iso.png` first. Use `front.png`, `right.png`, `top.png`, bounding boxes, areas, and volumes when needed.
6. If `status` is `error`, read `error` and `traceback`, fix the script, and submit again.
7. Iterate by submitting another job with the same `--project` and `--session`.

`out/latest_result.json` points to the last processed job across all projects. Prefer the project/session `current/result.json` when you know which model you are working on.

## Document Target Rules

Default behavior is session-based and safe for normal agent use.

- Use the default target unless the user explicitly asks otherwise.
- Use `--use-active-document` only when the user explicitly wants to modify the currently active FreeCAD document.
- Use `--new-document` only when the user explicitly wants a fresh FreeCAD document per run.
- Do not assume the foreground FreeCAD document is safe to modify.

## Rebuild Vs Update

Use `--mode rebuild` by default. It clears only the selected agent session document and runs the model script from scratch.

Use `--mode update` only when the model script is written to reuse stable object names and update existing FreeCAD objects. Update-mode scripts must be defensive:

- Find existing objects by stable `Name`.
- Create missing objects if needed.
- Avoid creating `Name001`, `Name002`, etc. duplicates during normal iteration.
- Hide cutters/intermediate objects if they are not part of the visible final model.

## Model Script Expectations

The macro injects these globals into the model script:

```python
App      # FreeCAD module
FreeCAD  # same as App
Gui      # FreeCADGui module, if available
DOC      # target FreeCAD document
JOB      # job dictionary
OUT_DIR  # output directory for this run
PARAMS   # dict from --param and --params-file
```

Prefer explicit, stable object names. Keep scripts deterministic from their inputs. Use `PARAMS` for dimensions and configuration that should change across iterations.

## Data Management

Use `agent_data.py` for inspection:

```bash
python3 agent_data.py list
python3 agent_data.py stats
```

Cleanup is destructive. Always run cleanup as a dry-run first. Only add `--apply` after the user confirms deletion.

Dry-run examples:

```bash
python3 agent_data.py prune --project <project> --session <session> --keep-runs 20
python3 agent_data.py compact --older-than 14d --keep-runs 10
```

Apply examples, only after user confirmation:

```bash
python3 agent_data.py prune --project <project> --session <session> --keep-runs 20 --apply
python3 agent_data.py compact --older-than 14d --keep-runs 10 --apply
```

Pinned runs are protected from cleanup:

```bash
python3 agent_data.py pin <project> <session> <run-id>
python3 agent_data.py unpin <project> <session> <run-id>
```

## Troubleshooting

If a submitted job does not produce `current/result.json`, check:

- FreeCAD is open.
- The macro was executed in FreeCAD.
- The job is still in `inbox/` or renamed to `.running`.
- `logs/freecad_folder_watch_agent.log` contains recent activity.

If `result.json` has an old `agent_version`, ask the user to reload the macro in FreeCAD.

If screenshots are missing but the model exists, inspect `result.json` for screenshot errors and retry after the user brings FreeCAD to a usable GUI state.

## Safety

This bridge executes local Python inside FreeCAD. Only run scripts from this repository or paths created for the user's current task. Do not submit untrusted downloaded scripts.

Do not delete `out/`, `runs/`, or generated exports unless the user explicitly confirms deletion after seeing a dry-run.
