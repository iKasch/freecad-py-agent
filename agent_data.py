#!/usr/bin/env python3
"""Inspect and clean FreeCAD folder-watch agent output data."""

import argparse
import json
import shutil
import time
from pathlib import Path


DEFAULT_ROOT = Path(__file__).parent.absolute()
HEAVY_SUFFIXES = {".fcstd", ".step", ".stl", ".3mf"}


def safe_name(value):
    cleaned = []
    for char in str(value):
        if char.isalnum() or char in ("-", "_"):
            cleaned.append(char)
        else:
            cleaned.append("_")
    name = "".join(cleaned).strip("_")
    return name or "default"


def read_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    tmp_path.replace(path)


def parse_duration(value):
    if value is None:
        return None
    value = value.strip().lower()
    if not value:
        raise argparse.ArgumentTypeError("Duration cannot be empty")

    unit = value[-1]
    number = value[:-1]
    multipliers = {
        "m": 60,
        "h": 60 * 60,
        "d": 24 * 60 * 60,
        "w": 7 * 24 * 60 * 60,
    }
    if unit not in multipliers:
        raise argparse.ArgumentTypeError("Use a duration like 12h, 14d, or 4w")
    try:
        return int(float(number) * multipliers[unit])
    except ValueError:
        raise argparse.ArgumentTypeError("Invalid duration: {}".format(value))


def format_bytes(value):
    amount = float(value)
    for unit in ("B", "KB", "MB", "GB"):
        if amount < 1024.0 or unit == "GB":
            if unit == "B":
                return "{} {}".format(int(amount), unit)
            return "{:.1f} {}".format(amount, unit)
        amount /= 1024.0


def round_number(value):
    try:
        return round(float(value), 3)
    except Exception:
        return value


def compact_bounding_box(box):
    if not box:
        return None
    return {
        "size": [
            round_number(box.get("x_length", 0.0)),
            round_number(box.get("y_length", 0.0)),
            round_number(box.get("z_length", 0.0)),
        ],
        "min": [
            round_number(box.get("x_min", 0.0)),
            round_number(box.get("y_min", 0.0)),
            round_number(box.get("z_min", 0.0)),
        ],
        "max": [
            round_number(box.get("x_max", 0.0)),
            round_number(box.get("y_max", 0.0)),
            round_number(box.get("z_max", 0.0)),
        ],
    }


def union_bounding_box(objects):
    boxes = [obj.get("bounding_box") for obj in objects if obj.get("bounding_box")]
    if not boxes:
        return None
    return {
        "x_min": min(box["x_min"] for box in boxes),
        "x_max": max(box["x_max"] for box in boxes),
        "y_min": min(box["y_min"] for box in boxes),
        "y_max": max(box["y_max"] for box in boxes),
        "z_min": min(box["z_min"] for box in boxes),
        "z_max": max(box["z_max"] for box in boxes),
        "x_length": max(box["x_max"] for box in boxes)
        - min(box["x_min"] for box in boxes),
        "y_length": max(box["y_max"] for box in boxes)
        - min(box["y_min"] for box in boxes),
        "z_length": max(box["z_max"] for box in boxes)
        - min(box["z_min"] for box in boxes),
    }


def screenshot_summary(screenshot):
    if isinstance(screenshot, dict):
        path = screenshot.get("path")
        summary = {
            "view": screenshot.get("view") or (Path(path).stem if path else None),
            "path": path,
        }
        if screenshot.get("error"):
            summary["error"] = screenshot.get("error")
        return summary
    path = str(screenshot)
    return {"view": Path(path).stem, "path": path}


def result_summary(result, max_objects=30):
    document = result.get("document") or {}
    objects = document.get("objects") or []
    visible_objects = [
        obj for obj in objects if obj.get("visible") is not False and obj.get("bounding_box")
    ]
    object_source = visible_objects or [obj for obj in objects if obj.get("bounding_box")]

    compact_objects = []
    for obj in object_source[:max_objects]:
        compact_objects.append(
            {
                "name": obj.get("name"),
                "label": obj.get("label"),
                "type_id": obj.get("type_id"),
                "size": (compact_bounding_box(obj.get("bounding_box")) or {}).get("size"),
                "volume": round_number(obj.get("volume")) if "volume" in obj else None,
            }
        )

    summary = {
        "status": result.get("status"),
        "agent_version": result.get("agent_version"),
        "project": result.get("project"),
        "session": result.get("session"),
        "run_id": result.get("run_id"),
        "run_number": result.get("run_number"),
        "started_at": result.get("started_at"),
        "finished_at": result.get("finished_at"),
        "current_dir": result.get("current_dir"),
        "output_dir": result.get("output_dir"),
        "document": {
            "name": document.get("name"),
            "label": document.get("label"),
            "object_count": document.get("object_count", 0),
            "visible_shape_count": len(visible_objects),
            "bounding_box": compact_bounding_box(union_bounding_box(object_source)),
            "objects": compact_objects,
        },
        "screenshots": [
            screenshot_summary(item) for item in (result.get("screenshots") or [])
        ],
        "exports": result.get("exports") or {},
    }

    omitted = max(0, len(object_source) - max_objects)
    if omitted:
        summary["document"]["omitted_object_count"] = omitted
    if result.get("error"):
        summary["error"] = result.get("error")
    if result.get("traceback"):
        summary["traceback_tail"] = "\n".join(result.get("traceback", "").splitlines()[-12:])
    return summary


def current_dir(root, project, session):
    return (
        projects_dir(root)
        / safe_name(project)
        / "sessions"
        / safe_name(session)
        / "current"
    )


def load_result_for_show(root, args):
    if args.run:
        result_dir = run_path(root, args.project, args.session, args.run)
    else:
        result_dir = current_dir(root, args.project, args.session)
    summary_path = result_dir / "result_summary.json"
    if summary_path.exists():
        return read_json(summary_path, {}), summary_path

    result_path = result_dir / "result.json"
    result = read_json(result_path, {})
    if not result:
        raise SystemExit("Result not found: {}".format(result_path))
    return result_summary(result, max_objects=args.max_objects), result_path


def print_human_summary(summary, source_path):
    document = summary.get("document") or {}
    print("source: {}".format(source_path))
    print(
        "status: {}  project: {}  session: {}  run: {}".format(
            summary.get("status"),
            summary.get("project"),
            summary.get("session"),
            summary.get("run_id"),
        )
    )
    if summary.get("error"):
        print("error: {}".format(summary.get("error")))
        if summary.get("traceback_tail"):
            print("traceback_tail:")
            print(summary.get("traceback_tail"))

    bbox = document.get("bounding_box") or {}
    if bbox.get("size"):
        print("overall size xyz: {}".format(" x ".join(str(v) for v in bbox["size"])))

    print(
        "objects: {} total, {} visible shapes".format(
            document.get("object_count", 0),
            document.get("visible_shape_count", 0),
        )
    )
    for obj in document.get("objects") or []:
        size = obj.get("size") or ["-", "-", "-"]
        print(
            "- {label} ({name}) size={size} volume={volume}".format(
                label=obj.get("label") or obj.get("name"),
                name=obj.get("name"),
                size=" x ".join(str(v) for v in size),
                volume=obj.get("volume"),
            )
        )
    if document.get("omitted_object_count"):
        print("- ... {} more objects omitted".format(document["omitted_object_count"]))

    screenshots = summary.get("screenshots") or []
    if screenshots:
        print("screenshots:")
        for screenshot in screenshots:
            suffix = " error={}".format(screenshot["error"]) if screenshot.get("error") else ""
            print("- {view}: {path}{suffix}".format(suffix=suffix, **screenshot))

    exports = summary.get("exports") or {}
    if exports:
        print("exports:")
        for key in sorted(exports):
            print("- {}: {}".format(key, exports[key]))


def print_brief_summary(summary):
    document = summary.get("document") or {}
    bbox = document.get("bounding_box") or {}
    size = bbox.get("size") or ["-", "-", "-"]
    status = summary.get("status")
    project = summary.get("project")
    session = summary.get("session")
    run_id = summary.get("run_id")
    visible_count = document.get("visible_shape_count", 0)
    object_count = document.get("object_count", 0)
    print(
        "status={} project={} session={} run={} size={} objects={}/{}".format(
            status,
            project,
            session,
            run_id,
            "x".join(str(value) for value in size),
            visible_count,
            object_count,
        )
    )
    if summary.get("error"):
        print("error={}".format(summary.get("error")))


def directory_size(path):
    total = 0
    if not path.exists():
        return total
    for item in path.rglob("*"):
        if item.is_file():
            try:
                total += item.stat().st_size
            except OSError:
                pass
    return total


def projects_dir(root):
    return root / "out" / "projects"


def iter_sessions(root, project=None, session=None):
    base = projects_dir(root)
    if not base.exists():
        return

    project_filter = safe_name(project) if project else None
    session_filter = safe_name(session) if session else None

    for project_dir in sorted(path for path in base.iterdir() if path.is_dir()):
        if project_filter and project_dir.name != project_filter:
            continue
        sessions_dir = project_dir / "sessions"
        if not sessions_dir.exists():
            continue
        for session_dir in sorted(path for path in sessions_dir.iterdir() if path.is_dir()):
            if session_filter and session_dir.name != session_filter:
                continue
            yield project_dir, session_dir


def run_dirs(session_dir):
    runs = session_dir / "runs"
    if not runs.exists():
        return []
    return sorted([path for path in runs.iterdir() if path.is_dir()], key=lambda p: p.name)


def selected_run_dirs(root, args):
    for _, session_dir in iter_sessions(root, args.project, args.session):
        meta = read_json(session_dir / "session.json", {})
        current_run = meta.get("current_run")
        runs = run_dirs(session_dir)
        keep = set(path.name for path in runs[-args.keep_runs :]) if args.keep_runs else set()
        cutoff = time.time() - args.older_than if args.older_than else None

        for run_dir in runs:
            if run_dir.name == current_run:
                continue
            if run_dir.name in keep:
                continue
            if (run_dir / ".pinned").exists():
                continue
            if cutoff is not None and run_dir.stat().st_mtime >= cutoff:
                continue
            yield session_dir, run_dir


def cmd_list(args):
    root = Path(args.root).expanduser().resolve()
    found = False
    for project_dir, session_dir in iter_sessions(root, args.project, args.session):
        found = True
        meta = read_json(session_dir / "session.json", {})
        runs = run_dirs(session_dir)
        current = meta.get("current_run", "-")
        print(
            "{}/{}  runs={}  current={}  updated={}".format(
                project_dir.name,
                session_dir.name,
                len(runs),
                current,
                meta.get("updated_at", "-"),
            )
        )
    if not found:
        print("No managed project/session output found.")


def cmd_stats(args):
    root = Path(args.root).expanduser().resolve()
    total_size = 0
    total_runs = 0
    for project_dir, session_dir in iter_sessions(root, args.project, args.session):
        size = directory_size(session_dir)
        runs = run_dirs(session_dir)
        total_size += size
        total_runs += len(runs)
        print(
            "{}/{}  runs={}  size={}".format(
                project_dir.name, session_dir.name, len(runs), format_bytes(size)
            )
        )
    print("total  runs={}  size={}".format(total_runs, format_bytes(total_size)))


def cmd_show(args):
    root = Path(args.root).expanduser().resolve()
    summary, source_path = load_result_for_show(root, args)
    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    elif args.brief:
        print_brief_summary(summary)
    else:
        print_human_summary(summary, source_path)


def cmd_prune(args):
    root = Path(args.root).expanduser().resolve()
    candidates = list(selected_run_dirs(root, args))
    if not candidates:
        print("Nothing to prune.")
        return

    for _, run_dir in candidates:
        print("{} {}".format("delete" if args.apply else "would delete", run_dir))
        if args.apply:
            shutil.rmtree(str(run_dir))

    if not args.apply:
        print("Dry run only. Add --apply to delete these run folders.")


def cmd_compact(args):
    root = Path(args.root).expanduser().resolve()
    candidates = list(selected_run_dirs(root, args))
    removed = 0
    for _, run_dir in candidates:
        heavy_files = [
            path
            for path in run_dir.rglob("*")
            if path.is_file() and path.suffix.lower() in HEAVY_SUFFIXES
        ]
        if not heavy_files:
            continue
        for path in heavy_files:
            print("{} {}".format("delete" if args.apply else "would delete", path))
            if args.apply:
                path.unlink()
            removed += 1

    if removed == 0:
        print("Nothing to compact.")
    elif not args.apply:
        print("Dry run only. Add --apply to delete these heavy files.")


def run_path(root, project, session, run):
    return (
        projects_dir(root)
        / safe_name(project)
        / "sessions"
        / safe_name(session)
        / "runs"
        / run
    )


def cmd_pin(args):
    root = Path(args.root).expanduser().resolve()
    path = run_path(root, args.project, args.session, args.run)
    if not path.is_dir():
        raise SystemExit("Run not found: {}".format(path))
    marker = path / ".pinned"
    if args.pinned:
        marker.write_text("pinned_at={}\n".format(time.strftime("%Y-%m-%dT%H:%M:%S%z")), encoding="utf-8")
        print("pinned {}".format(path))
    else:
        if marker.exists():
            marker.unlink()
        print("unpinned {}".format(path))


def add_selection_args(parser):
    parser.add_argument("--project", help="Project id to inspect or clean")
    parser.add_argument("--session", help="Session id to inspect or clean")


def add_cleanup_args(parser):
    add_selection_args(parser)
    parser.add_argument(
        "--keep-runs",
        type=int,
        default=20,
        help="Keep the newest N runs per session. Defaults to 20.",
    )
    parser.add_argument(
        "--older-than",
        type=parse_duration,
        help="Only select runs older than this duration, for example 14d.",
    )
    parser.add_argument("--apply", action="store_true", help="Actually delete data.")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Inspect and clean FreeCAD folder-watch agent output data."
    )
    parser.add_argument(
        "--root",
        default=str(DEFAULT_ROOT),
        help="Bridge root folder. Defaults to this script's folder.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List managed sessions")
    add_selection_args(list_parser)
    list_parser.set_defaults(func=cmd_list)

    stats_parser = subparsers.add_parser("stats", help="Show disk usage")
    add_selection_args(stats_parser)
    stats_parser.set_defaults(func=cmd_stats)

    show_parser = subparsers.add_parser(
        "show", help="Show a compact current result summary"
    )
    show_parser.add_argument("--project", required=True, help="Project id to inspect")
    show_parser.add_argument("--session", required=True, help="Session id to inspect")
    show_parser.add_argument("--run", help="Specific historical run id")
    show_parser.add_argument(
        "--max-objects",
        type=int,
        default=30,
        help="Maximum object summaries when deriving from full result.json.",
    )
    show_parser.add_argument(
        "--json", action="store_true", help="Print compact summary as JSON"
    )
    show_parser.add_argument(
        "--brief", action="store_true", help="Print a one-line status summary"
    )
    show_parser.set_defaults(func=cmd_show)

    prune_parser = subparsers.add_parser("prune", help="Delete old run folders")
    add_cleanup_args(prune_parser)
    prune_parser.set_defaults(func=cmd_prune)

    compact_parser = subparsers.add_parser(
        "compact", help="Delete heavy export files from old runs"
    )
    add_cleanup_args(compact_parser)
    compact_parser.set_defaults(func=cmd_compact)

    pin_parser = subparsers.add_parser("pin", help="Protect one run from cleanup")
    pin_parser.add_argument("project")
    pin_parser.add_argument("session")
    pin_parser.add_argument("run")
    pin_parser.set_defaults(func=cmd_pin, pinned=True)

    unpin_parser = subparsers.add_parser("unpin", help="Allow one run to be cleaned")
    unpin_parser.add_argument("project")
    unpin_parser.add_argument("session")
    unpin_parser.add_argument("run")
    unpin_parser.set_defaults(func=cmd_pin, pinned=False)

    return parser.parse_args()


def main():
    args = parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
