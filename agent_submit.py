#!/usr/bin/env python3
"""Submit a Python model script to the FreeCAD folder-watch agent."""

import argparse
import json
import os
import shutil
import time
from pathlib import Path


DEFAULT_ROOT = Path(__file__).resolve().parent


def safe_name(value):
    cleaned = []
    for char in str(value):
        if char.isalnum() or char in ("-", "_"):
            cleaned.append(char)
        else:
            cleaned.append("_")
    name = "".join(cleaned).strip("_")
    return name or "freecad_agent_job"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Submit a FreeCAD Python script to the running folder-watch macro."
    )
    parser.add_argument("script", help="Path to the Python script FreeCAD should run")
    parser.add_argument(
        "--root",
        default=os.environ.get("FREECAD_AGENT_ROOT", str(DEFAULT_ROOT)),
        help="Bridge root folder. Defaults to this script's folder.",
    )
    parser.add_argument("--id", dest="job_id", help="Optional stable job id")
    parser.add_argument("--title", help="Optional document/output title")
    parser.add_argument(
        "--session",
        default="default",
        help="Reusable FreeCAD agent document/session name. Defaults to 'default'.",
    )
    parser.add_argument(
        "--views",
        default="iso,front,right,top",
        help="Comma-separated screenshots to capture. Known: iso,front,rear,right,left,top,bottom.",
    )
    parser.add_argument("--width", type=int, default=1400, help="Screenshot width")
    parser.add_argument("--height", type=int, default=1000, help="Screenshot height")
    target_group = parser.add_mutually_exclusive_group()
    target_group.add_argument(
        "--use-active-document",
        action="store_true",
        help="Run the script in the current active FreeCAD document. Default: create a new document and leave existing documents untouched.",
    )
    target_group.add_argument(
        "--new-document",
        action="store_true",
        help="Create a fresh FreeCAD document for this job instead of reusing the session document.",
    )
    parser.add_argument(
        "--restore-active-document",
        action="store_true",
        help="After rendering, switch FreeCAD back to the previously active document.",
    )
    parser.add_argument("--step", action="store_true", help="Also export STEP")
    parser.add_argument("--stl", action="store_true", help="Also export STL")
    parser.add_argument(
        "--no-fcstd", action="store_true", help="Do not save a FreeCAD .FCStd file"
    )
    return parser.parse_args()


def atomic_write_text(path, text):
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(text, encoding="utf-8")
    tmp_path.replace(path)


def main():
    args = parse_args()
    root = Path(args.root).expanduser().resolve()
    inbox = root / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)

    source_script = Path(args.script).expanduser().resolve()
    if not source_script.exists():
        raise SystemExit("Script not found: {}".format(source_script))

    timestamp = time.strftime("%Y%m%d-%H%M%S")
    base = safe_name(args.title or source_script.stem)
    job_id = safe_name(args.job_id or "{}-{}".format(timestamp, base))
    session = safe_name(args.session)
    target_document = "session"
    if args.use_active_document:
        target_document = "active"
    elif args.new_document:
        target_document = "new"

    copied_script = inbox / "{}.py".format(job_id)
    tmp_script = copied_script.with_suffix(".py.tmp")
    shutil.copyfile(source_script, tmp_script)
    tmp_script.replace(copied_script)

    views = [item.strip() for item in args.views.split(",") if item.strip()]
    job = {
        "id": job_id,
        "session": session,
        "script_path": str(copied_script),
        "document_name": safe_name("Agent_{}".format(session)),
        "document_label": "Agent {}".format(session),
        "job_title": args.title or base,
        "output_name": safe_name(args.title or job_id),
        "reset_document": False,
        "restore_active_document": args.restore_active_document,
        "target_document": target_document,
        "views": views,
        "screenshot_width": args.width,
        "screenshot_height": args.height,
        "exports": {
            "fcstd": not args.no_fcstd,
            "step": args.step,
            "stl": args.stl,
        },
        "submitted_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }

    job_path = inbox / "{}.json".format(job_id)
    atomic_write_text(job_path, json.dumps(job, indent=2, sort_keys=True))

    print("submitted {}".format(job_id))
    print("job: {}".format(job_path))
    print("result: {}".format(root / "out" / job_id / "result.json"))


if __name__ == "__main__":
    main()
