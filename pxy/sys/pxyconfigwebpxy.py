#!/usr/bin/env python3
"""Safely read and update literal runtime settings in syscnfgpxy.py."""

import ast
import datetime
import fcntl
import json
import math
import os
from pathlib import Path
import re
import runpy
import shutil
import stat
import sys
import tempfile
import time


CONFIG_PATH = Path(__file__).with_name("syscnfgpxy.py")
ENUMS = {
    "SYSMODEPXY_RUN_MODE": ("PRD", "CHK", "SIM"),
    "SYSDTAFPXY_SELECTED_MODE": tuple(str(mode) for mode in range(9))
    + tuple(f"{side}{trend}" for side in range(9) for trend in range(9)),
    "EXEOTMPXY_STRIKE_MODE": ("ATM", "OTMFIX", "OTMDYN"),
    "SYSENTRPXY_SIGNAL_MODE": ("MKT", "STS"),
    "SYSSMAPXY_VARIANT": ("SMA", "TSMA"),
    "RUNEXACPXY_CNTRLRSKBAR": ("YES", "NO"),
    "EXECBUYPXY_ACTION": ("YES", "NO"),
}
CHOICES = {
    "SYSDTAFPXY_DEFAULT_INTERVAL": ("1m", "2m", "5m", "15m", "30m", "60m", "1h", "1d"),
    "SYSPLCHRTPXY_FETCH_INTERVAL": ("1m", "2m", "5m", "15m", "30m", "60m", "1h", "1d"),
    "SYSPLCHRTPXY_OHLC_MODE": (1, 2, 3, 4, 5, 6),
    "SYSKATRPXY_ATR_MODE": (1, 2, 3),
}
OPTIONAL_DEFAULTS = {
    "EXEOTMPXY_STRIKE_MODE": "ATM",
    "EXEOTMPXY_FIXED_DISTANCE": 100,
    "EXEOTMPXY_DYNAMIC_WEEKDAY_DISTANCES": (200, 150, 100, 50, 0),
}
HIDDEN_PARTS = ("SECRET", "TOKEN", "PASSWORD", "API_KEY")
SIGNED_PARTS = ("PNL", "LOSS", "FLOOR", "THRESHOLD")
TIME_PARTS = ("SECONDS", "TIMEOUT", "DELAY", "POLL", "GAP", "KEEP")
COUNT_PARTS = ("ATTEMPTS", "RETRIES", "ITERATIONS", "LAYERS", "ROWS", "WINDOW", "PERIOD")


def _safe_literal(node):
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "dt_time":
        if not all(isinstance(arg, ast.Constant) and isinstance(arg.value, int) for arg in node.args):
            raise ValueError("time values must use integer components")
        if node.keywords:
            allowed = {"hour", "minute", "second", "microsecond"}
            if any(keyword.arg not in allowed or not isinstance(keyword.value, ast.Constant)
                   or not isinstance(keyword.value.value, int) for keyword in node.keywords):
                raise ValueError("unsupported time value")
            parts = [0, 0, 0, 0]
            for keyword in node.keywords:
                parts[{"hour": 0, "minute": 1, "second": 2, "microsecond": 3}[keyword.arg]] = keyword.value.value
        else:
            parts = [arg.value for arg in node.args]
            parts.extend([0] * (4 - len(parts)))
        return datetime.time(*parts)
    return ast.literal_eval(node)


def _assignments(source):
    tree = ast.parse(source, filename=str(CONFIG_PATH))
    result = {}
    top_level = set(tree.body)
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if len(targets) != 1 or not isinstance(targets[0], ast.Name):
            continue
        name = targets[0].id
        if not name.isupper():
            continue
        result[name] = {
            "node": node,
            "value_node": node.value,
            "editable": node in top_level,
        }
    return result


def _kind(value):
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, datetime.time):
        return "time"
    if isinstance(value, (dict, list, tuple)):
        return "json"
    return "unsupported"


def _metadata(source):
    assignments = _assignments(source)
    values = []
    for name, entry in assignments.items():
        node = entry["node"]
        try:
            value = _safe_literal(entry["value_node"])
            kind = _kind(value)
            display = value.isoformat() if isinstance(value, datetime.time) else value
            editable = entry["editable"] and kind != "unsupported"
        except (ValueError, TypeError, SyntaxError):
            kind = "derived"
            display = ast.get_source_segment(source, entry["value_node"]) or "Derived at runtime"
            editable = False

        if any(part in name for part in HIDDEN_PARTS):
            display = "[redacted]"
            editable = False

        values.append({
            "key": name,
            "owner": name.split("_", 1)[0],
            "kind": kind,
            "value": display,
            "editable": editable,
            "options": list(ENUMS.get(name, CHOICES.get(name, ()))),
        })
    for name, value in OPTIONAL_DEFAULTS.items():
        if name in assignments:
            continue
        values.append({
            "key": name,
            "owner": name.split("_", 1)[0],
            "kind": _kind(value),
            "value": value,
            "editable": True,
            "options": list(ENUMS.get(name, CHOICES.get(name, ()))),
        })
    return values, assignments


def _encode_value(name, value, current):
    if name in ENUMS or name in CHOICES:
        if value not in ENUMS.get(name, CHOICES.get(name, ())):
            raise ValueError(f"{name} must be one of its listed choices")
    if isinstance(current, bool):
        if not isinstance(value, bool):
            raise ValueError(f"{name} must be true or false")
        return "True" if value else "False"
    if isinstance(current, int) and not isinstance(current, bool):
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError(f"{name} must be an integer")
        _validate_number(name, value)
        return str(value)
    if isinstance(current, float):
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
            raise ValueError(f"{name} must be a finite number")
        _validate_number(name, value)
        return repr(float(value))
    if isinstance(current, str):
        if not isinstance(value, str):
            raise ValueError(f"{name} must be text")
        if len(value) > 4096:
            raise ValueError(f"{name} is too long")
        if name.endswith("_SELECTED_MODE") and not re.fullmatch(r"[0-8]{1,2}", value):
            raise ValueError(f"{name} must contain one or two digits from 0 to 8")
        return repr(value)
    if isinstance(current, datetime.time):
        if not isinstance(value, str):
            raise ValueError(f"{name} must be a time")
        try:
            parsed = datetime.time.fromisoformat(value)
        except ValueError as error:
            raise ValueError(f"{name} must be a valid 24-hour time") from error
        return f"dt_time({parsed.hour}, {parsed.minute}, {parsed.second}, {parsed.microsecond})"
    if isinstance(current, (dict, list, tuple)):
        expected = list if isinstance(current, tuple) else type(current)
        if not isinstance(value, expected):
            raise ValueError(f"{name} must keep its current {expected.__name__} structure")
        if len(value) > 100 or not _safe_json_value(value):
            raise ValueError(f"{name} must contain at most 100 JSON-safe items")
        if not _same_shape(current, value):
            raise ValueError(f"{name} must preserve its existing value types")
        if isinstance(current, dict) and value.keys() != current.keys():
            raise ValueError(f"{name} must preserve its existing keys")
        if isinstance(current, (list, tuple)) and len(value) != len(current):
            raise ValueError(f"{name} must preserve its existing item count")
        if isinstance(current, tuple):
            return repr(tuple(value))
        return repr(value)
    raise ValueError(f"{name} is not editable")


def _validate_number(name, value):
    if abs(value) > 1_000_000_000:
        raise ValueError(f"{name} is outside the supported numeric range")
    if not any(part in name for part in SIGNED_PARTS) and value < 0:
        raise ValueError(f"{name} cannot be negative")
    if any(part in name for part in TIME_PARTS) and value > 86_400:
        raise ValueError(f"{name} cannot exceed one day")
    if any(part in name for part in COUNT_PARTS) and value > 1_000_000:
        raise ValueError(f"{name} exceeds the supported count limit")


def _safe_json_value(value, depth=0):
    if depth > 10:
        return False
    if value is None or isinstance(value, (bool, int, str)):
        if isinstance(value, str):
            return len(value) <= 4096
        return not isinstance(value, int) or isinstance(value, bool) or abs(value) <= 1_000_000_000
    if isinstance(value, float):
        return math.isfinite(value) and abs(value) <= 1_000_000_000
    if isinstance(value, list):
        return len(value) <= 100 and all(_safe_json_value(item, depth + 1) for item in value)
    if isinstance(value, dict):
        return len(value) <= 100 and all(
            isinstance(key, str) and _safe_json_value(item, depth + 1)
            for key, item in value.items()
        )
    return False


def _same_shape(current, updated):
    if isinstance(current, bool):
        return isinstance(updated, bool)
    if isinstance(current, int):
        return isinstance(updated, int) and not isinstance(updated, bool)
    if isinstance(current, float):
        return isinstance(updated, (int, float)) and not isinstance(updated, bool)
    if isinstance(current, str):
        return isinstance(updated, str)
    if isinstance(current, dict):
        return (
            isinstance(updated, dict)
            and current.keys() == updated.keys()
            and all(_same_shape(current[key], updated[key]) for key in current)
        )
    if isinstance(current, (list, tuple)):
        return (
            isinstance(updated, (list, tuple))
            and len(current) == len(updated)
            and all(_same_shape(old, new) for old, new in zip(current, updated))
        )
    return False


def _line_offset(source, lineno, byte_column):
    lines = source.splitlines(keepends=True)
    prefix = sum(len(line) for line in lines[:lineno - 1])
    current_line = lines[lineno - 1]
    char_column = len(current_line.encode("utf-8")[:byte_column].decode("utf-8"))
    return prefix + char_column


def _write(updates):
    lock_path = CONFIG_PATH.with_name(f".{CONFIG_PATH.name}.lock")
    with lock_path.open("a", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            return _write_locked(updates)
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def _write_locked(updates):
    if not isinstance(updates, dict) or not updates:
        raise ValueError("Provide at least one setting to update")
    original = CONFIG_PATH.read_text(encoding="utf-8")
    _, assignments = _metadata(original)
    edits = []
    additions = []
    for name, value in updates.items():
        entry = assignments.get(name)
        if entry is None:
            if name not in OPTIONAL_DEFAULTS:
                raise ValueError(f"{name} is not an editable runtime setting")
            replacement = _encode_value(name, value, OPTIONAL_DEFAULTS[name])
            additions.append(f"{name} = {replacement}")
            continue
        if not entry["editable"]:
            raise ValueError(f"{name} is not an editable runtime setting")
        current = _safe_literal(entry["value_node"])
        replacement = _encode_value(name, value, current)
        node = entry["value_node"]
        start = _line_offset(original, node.lineno, node.col_offset)
        end = _line_offset(original, node.end_lineno, node.end_col_offset)
        edits.append((start, end, replacement))

    updated = original
    for start, end, replacement in sorted(edits, reverse=True):
        updated = updated[:start] + replacement + updated[end:]
    if additions:
        updated = updated.rstrip() + "\n\n" + "\n".join(additions) + "\n"

    ast.parse(updated, filename=str(CONFIG_PATH))
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(prefix=".syscnfgpxy.", suffix=".tmp", dir=CONFIG_PATH.parent)
    backup_name = CONFIG_PATH.with_name(f"{CONFIG_PATH.name}.{time.time_ns()}.bak")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as temp_file:
            temp_file.write(updated)
            temp_file.flush()
            os.fsync(temp_file.fileno())
        os.chmod(temp_name, stat.S_IMODE(CONFIG_PATH.stat().st_mode))
        runpy.run_path(temp_name, run_name="__pxy_config_validation__")
        shutil.copy2(CONFIG_PATH, backup_name)
        os.replace(temp_name, CONFIG_PATH)
        directory_fd = os.open(CONFIG_PATH.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise
    return {"updated": sorted(updates), "backup": backup_name.name}


def main():
    try:
        action = sys.argv[1] if len(sys.argv) > 1 else ""
        if action == "read":
            source = CONFIG_PATH.read_text(encoding="utf-8")
            values, _ = _metadata(source)
            result = {"ok": True, "settings": values}
        elif action == "write":
            request = json.load(sys.stdin)
            result = {"ok": True, **_write(request.get("updates"))}
        else:
            raise ValueError("Expected read or write action")
        print(json.dumps(result, allow_nan=False))
    except Exception as error:
        print(json.dumps({"ok": False, "error": str(error)}))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
