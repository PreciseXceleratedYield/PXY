#!/usr/bin/env python3
"""Independent read-only PXY Telegram Control Tower.

No imports from trading modules, no broker calls, no orders, no engine control.
"""
import ast
import html
import socket
import json
import os
import re
import shutil
import subprocess
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

APP = Path(__file__).resolve().parent
ROOT = APP.parent
HOME = Path.home()
STATE_DIR = HOME / ".pxy" / "tlgr"
STATE_PATH = STATE_DIR / "state.json"
CONFIG_PATH = STATE_DIR / "config.json"
LOG_PATH = STATE_DIR / "notifications.jsonl"
EVENT_PATH = STATE_DIR / "events.jsonl"
WEB = ROOT / "web"
TZ = ZoneInfo("Asia/Kolkata")
CHECK_SECONDS = 30
BOOK_SECONDS = 300
EVENT_WINDOW = (9 * 60 + 15, 9 * 60 + 35)
REPORTS = {555: "TAKEOFF", 575: "AIRBORNE", 920: "DESCENDING", 941: "TOUCHDOWN"}
PATTERN = re.compile(r"traceback|(?:^|\W)(?:error|failed|failure|timeout|exception|critical|warning|stale)(?:\W|$)", re.I)
ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def now():
    return datetime.now(TZ)


def write_jsonl(path, event):
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        if path.exists() and path.stat().st_size > 5 * 1024 * 1024:
            path.replace(path.with_suffix(".jsonl.1"))
        with path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")
    except OSError:
        pass


def save(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    temp = STATE_PATH.with_suffix(".tmp")
    temp.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    os.replace(temp, STATE_PATH)


def load():
    try:
        value = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def credentials():
    token = os.environ.get("PXY_TLGR_BOT_TOKEN", "")
    chat = os.environ.get("PXY_TLGR_CHAT_ID", "")
    if token and chat:
        return token, chat
    # Read existing constants without importing/running the trading engine.
    try:
        source = ast.parse((APP / "sysexepxy.py").read_text(encoding="utf-8"))
        values = {}
        for node in source.body:
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id in {"TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"}:
                        values[target.id] = str(node.value.value)
        return token or values.get("TELEGRAM_BOT_TOKEN", ""), chat or values.get("TELEGRAM_CHAT_ID", "")
    except (OSError, SyntaxError):
        return token, chat


def send(state, key, category, message):
    if key in state.setdefault("sent", {}):
        return True
    token, chat = credentials()
    if not token or not chat:
        write_jsonl(LOG_PATH, {"time": now().isoformat(), "key": key, "category": category, "status": "UNCONFIGURED"})
        return False
    payload = urllib.parse.urlencode({"chat_id": chat, "text": message, "parse_mode": "HTML"}).encode()
    try:
        with urllib.request.urlopen(
            urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=payload),
            timeout=5,
        ) as response:
            result = json.load(response)
        if not result.get("ok"):
            raise RuntimeError("Telegram rejected notification")
        state["sent"][key] = now().isoformat()
        write_jsonl(LOG_PATH, {"time": now().isoformat(), "key": key, "category": category, "status": "SENT", "telegram_message_id": result.get("result", {}).get("message_id"), "message": message})
        save(state)
        return True
    except Exception as exc:
        write_jsonl(LOG_PATH, {"time": now().isoformat(), "key": key, "category": category, "status": "FAILED", "error": type(exc).__name__})
        return False


def fresh_json(name, max_age=600):
    path = WEB / (name + ".json")
    try:
        if time.time() - path.stat().st_mtime > max_age:
            return None
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def running(name):
    try:
        return subprocess.run(["systemctl", "is-active", "--quiet", name], timeout=2).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def engine_alive():
    try:
        result = subprocess.run(["pgrep", "-f", "[s]ysexepxy.py"], capture_output=True, timeout=2)
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def field(label, value):
    """Ten-character label, then space-colon-space; HTML-safe values."""
    return f"{label:<10}: {html.escape(str(value))}"


def safe_number(value):
    try:
        return float(value)
    except (TypeError, ValueError, OverflowError):
        return None


def money(value):
    if value is None:
        return "NA"
    return f"{'+' if value > 0 else '-' if value < 0 else ''}₹{abs(value):,.0f}"


def service_web():
    try:
        return subprocess.run(["pgrep", "-f", "[n]ode pxy.js"], capture_output=True, timeout=2).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def uptime():
    try:
        result = subprocess.run(["ps", "-eo", "etimes,args"], capture_output=True, text=True, timeout=2)
        for line in result.stdout.splitlines():
            if "sysexepxy.py" in line and "grep" not in line:
                seconds = int(line.strip().split(None, 1)[0])
                return f"{seconds // 3600:02d}:{seconds // 60 % 60:02d}:{seconds % 60:02d}"
    except (OSError, ValueError, subprocess.TimeoutExpired):
        pass
    return "NA"


def counts(state):
    today = now().date().isoformat()
    issues = state.get("issues", {})
    errors = sum(1 for x in issues.values() if x.get("first", "").startswith(today) and x.get("severity") == "ERROR")
    warnings = sum(1 for x in issues.values() if x.get("first", "").startswith(today) and x.get("severity") == "WARNING")
    # Persisted counters are incremented when each distinct incident is first observed.
    daily = state.get("daily_incidents", {}).get(today, {})
    return daily.get("ERROR", errors), daily.get("WARNING", warnings)


def snapshot_report(title, state=None):
    state = state or {}
    stamp = now()
    positions = fresh_json("webpospxy")
    trades = fresh_json("webpnlpxy")
    engine = engine_alive()
    web = service_web()
    watch = running("pxywatch.service")
    ce = pe = None
    invested = current = open_pnl = None
    if isinstance(positions, list):
        ce = pe = 0
        invested = current = open_pnl = 0.0
        complete = True
        for item in positions:
            if not isinstance(item, dict):
                complete = False
                continue
            qty = safe_number(item.get("QTY"))
            symbol = str(item.get("SYMBOL", "")).upper()
            if qty is None:
                complete = False
                continue
            if "CE" in symbol:
                ce += qty
            elif "PE" in symbol:
                pe += qty
            value = safe_number(item.get("PNL"))
            if value is None:
                complete = False
            else:
                open_pnl += value
        if not complete:
            invested = current = open_pnl = None
    closed = []
    if isinstance(trades, list):
        closed = [r for r in trades if isinstance(r, dict) and str(r.get("Status", "")).upper() == "CLOSED"]
    books = len({str(r["Book_ID"]) for r in closed if r.get("Book_ID") is not None}) if isinstance(trades, list) else None
    values = [safe_number(r.get("PNL")) for r in closed]
    closed_pnl = sum(values) if isinstance(trades, list) and all(v is not None for v in values) else None
    net = closed_pnl + open_pnl if closed_pnl is not None and open_pnl is not None else None
    errors, warnings = counts(state)
    health = engine and web and watch
    landed = title == "TOUCHDOWN" and ce == 0 and pe == 0 and health
    status = ("LANDED SAFELY" if landed else "ATTENTION" if not health or (title == "TOUCHDOWN" and not landed)
              else title if title != "TAKEOFF" else "READY")
    greeting = "Good Evening" if title == "TOUCHDOWN" else "Good Afternoon" if title == "DESCENDING" else "Good Morning"
    emoji = {"TAKEOFF": "🚀", "AIRBORNE": "✈️", "DESCENDING": "🛬", "TOUCHDOWN": "🛬"}[title]
    lines = [
        f"Hello {html.escape(socket.gethostname())}, {greeting}! ",
        "",
        f"{emoji} PXY — {title}",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        field("Date", stamp.strftime("%d-%b-%Y")),
        field("Engine", "RUNNING" if engine else "STOPPED"),
        field("WebPXY", "RUNNING" if web else "STOPPED"),
        field("Watchdog", "RUNNING" if watch else "STOPPED"),
        field("Control", "RUNNING"),
        field("Broker", "NA"),
        field("Market", "CLOSED" if title == "TOUCHDOWN" else "NA"),
        field("Uptime", uptime()),
        field("Data Age", "NA"),
    ]
    if title == "TAKEOFF":
        lines += [field("Funds", "NA"), field("Positions", f"CE: {ce:g} | PE: {pe:g}" if ce is not None and pe is not None else "NA")]
    else:
        lines += [field("CE", f"{ce:g}" if ce is not None else "NA"),
                  field("PE", f"{pe:g}" if pe is not None else "NA"),
                  field("Invested", money(invested)),
                  field("Current", money(current)),
                  field("Open PnL", money(open_pnl)),
                  field("Closed PnL", money(closed_pnl)),
                  field("Net PnL", money(net))]
        if title in {"AIRBORNE", "TOUCHDOWN"}:
            lines += [field("PnL %" if title == "AIRBORNE" else "Return %", "NA")]
        if title == "TOUCHDOWN":
            wins = sum(1 for r in closed if (safe_number(r.get("PNL")) or 0) > 0)
            losses = sum(1 for r in closed if (safe_number(r.get("PNL")) or 0) < 0)
            lines += [field("Wins", wins if books is not None else "NA"),
                      field("Losses", losses if books is not None else "NA")]
    lines += [field("Books", f"{books} Closed" if books is not None else "NA"),
              field("Errors", f"{errors} Reported"),
              field("Warnings", f"{warnings} Reported"),
              "━━━━━━━━━━━━━━━━━━━━━━━━",
              field("Status", status)]
    if title == "TOUCHDOWN":
        lines += ["━━━━━━━━━━━━━━━━━━━━━━━━", "🏆 <b>FINAL NET PNL</b>", f"<b>{html.escape(money(net))}</b>"]
    # Preformatted content keeps ten-character label alignment in Telegram.
    header = "\n".join(lines[:3])
    detail = "\n".join(lines[3:-2] if title == "TOUCHDOWN" else lines[3:])
    if title == "TOUCHDOWN":
        return header + "\n<pre>" + detail + "</pre>\n" + "\n".join(lines[-2:])
    return header + "\n<pre>" + detail + "</pre>"


def trading_day(day):
    if day.weekday() >= 5:
        return False
    cache = HOME / ".pxy" / "cache" / "nse_fo_holidays.json"
    try:
        data = json.loads(cache.read_text(encoding="utf-8"))
        if day.isoformat() in data.get("holidays", []):
            return False
        # Fail closed on missing or outdated calendar; no external network requests.
        if datetime.fromisoformat(data["fetched_on"]).date() < day - timedelta(days=7):
            return False
        return True
    except (OSError, ValueError, KeyError):
        return False


def scan_books(state):
    trades = fresh_json("webpnlpxy")
    if not isinstance(trades, list):
        return
    books = {}
    for row in trades:
        if not isinstance(row, dict):
            continue
        book = row.get("Book_ID")
        if book is None:
            continue
        books.setdefault(str(book), []).append(row)
    day = now().date().isoformat()
    for book, rows in books.items():
        if any(str(r.get("Status", "")).upper() == "OPEN" for r in rows):
            continue
        if not rows or any(str(r.get("Status", "")).upper() != "CLOSED" for r in rows):
            continue
        # The first snapshot establishes a baseline, avoiding historical alert floods.
        key = f"book:{day}:{book}"
        if not state.get("book_initialized"):
            state.setdefault("sent", {})[key] = "BASELINE"
            continue
        pnl = sum(float(r.get("PNL", 0) or 0) for r in rows)
        times = [str(r.get("Exit_Time", "")) for r in rows if r.get("Exit_Time")]
        message = f"PXY 📕 Book #{book} CLOSED\nExit: {max(times) if times else 'unavailable'}\nRealized P&L: ₹{pnl:,.0f} (ledger estimate, before charges)"
        send(state, key, "BOOK", message)
    state["book_initialized"] = True
    save(state)


def capture_lines(state):
    try:
        proc = subprocess.run(
            ["tmux", "capture-pane", "-p", "-t", "pxy-engine", "-S", "-500", "-J"],
            capture_output=True, text=True, timeout=3, errors="replace",
        )
        if proc.returncode:
            return []
        lines = [ANSI.sub("", line).strip() for line in proc.stdout.splitlines() if line.strip()]
        # Overlap-based polling is best effort: a burst of >500 lines may be missed.
        old = state.get("tail", [])
        overlap = 0
        for count in range(min(len(old), len(lines)), 0, -1):
            if old[-count:] == lines[:count]:
                overlap = count
                break
        if not old:
            new = []
        elif overlap:
            new = lines[overlap:]
        elif lines == old:
            new = []
        else:
            new = lines  # pane reset / scrollback overflow
        state["tail"] = lines[-500:]
        return new
    except (OSError, subprocess.TimeoutExpired):
        return []


def scan_events(state):
    stamp = now()
    minutes = stamp.hour * 60 + stamp.minute
    for line in capture_lines(state):
        if not PATTERN.search(line):
            continue
        # Never put raw terminal content (potentially credentials) in Telegram.
        signature = re.sub(r"\\d+", "#", line)[:100]
        key = signature
        issue = state.setdefault("issues", {}).setdefault(key, {"first": stamp.isoformat(), "last": stamp.isoformat(), "alerted": False})
        issue["last"] = stamp.isoformat()
        write_jsonl(EVENT_PATH, {"time": stamp.isoformat(), "signature": signature, "status": "OBSERVED"})
        age = (stamp - datetime.fromisoformat(issue["first"])).total_seconds()
        if age >= 120 and (minutes < EVENT_WINDOW[1] or state.get("events_enabled", False)):
            if not issue["alerted"]:
                msg = f"PXY ⚠️ Persistent terminal warning\nDetected pattern: {signature[:80]}\nDuration: {age:.0f}s"
                if send(state, f"event:{stamp.date()}:{key}:{issue['first']}", "EVENT", msg):
                    issue["alerted"] = True
    for key, issue in list(state.setdefault("issues", {}).items()):
        last = datetime.fromisoformat(issue["last"])
        if (stamp - last).total_seconds() > 120:
            if issue["alerted"] and (minutes < EVENT_WINDOW[1] or state.get("events_enabled", False)):
                send(state, f"recovery:{stamp.date()}:{key}:{issue['first']}", "RECOVERY", "PXY ℹ️ No further matching terminal warnings observed for 120 seconds; verify component health.")
            del state["issues"][key]
    save(state)


def events_enabled():
    try:
        return bool(json.loads(CONFIG_PATH.read_text(encoding="utf-8")).get("events_enabled", False))
    except (OSError, ValueError):
        return False


def main():
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state = load()
    state.setdefault("events_enabled", False)
    last_book = 0.0
    last_date = state.get("session_date", "")
    while True:
        try:
            stamp = now()
            state["events_enabled"] = events_enabled()
            day = stamp.date()
            minute = stamp.hour * 60 + stamp.minute
            if day.isoformat() != last_date:
                last_date = day.isoformat()
                state["session_date"] = last_date
                state["book_initialized"] = False
                state["tail"] = []
                state["issues"] = {}
            if trading_day(day) and 555 <= minute <= 945:
                for target, title in REPORTS.items():
                    if target <= minute < target + 2:
                        send(state, f"report:{day}:{target}", "REPORT", snapshot_report(title, state))
                if 555 <= minute < 941:
                    scan_events(state)
                    if time.monotonic() - last_book >= BOOK_SECONDS:
                        scan_books(state)
                        last_book = time.monotonic()
            save(state)
        except Exception as exc:
            write_jsonl(EVENT_PATH, {"time": now().isoformat(), "status": "MONITOR_ERROR", "error": type(exc).__name__})
        time.sleep(CHECK_SECONDS)


if __name__ == "__main__":
    main()
