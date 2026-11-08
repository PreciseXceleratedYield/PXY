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


def _whatsapp_credentials():
    """WhatsApp credentials are supplied only by the service environment."""
    return os.environ.get("PXY_WHATSAPP_PHONE", "").strip(), os.environ.get("PXY_WHATSAPP_API_KEY", "").strip()


def _whatsapp_send(message):
    phone, api_key = _whatsapp_credentials()
    if not phone or not api_key or not re.fullmatch(r"[1-9][0-9]{7,14}", phone):
        return False, "UNCONFIGURED", None
    # Telegram uses HTML formatting; WhatsApp receives equivalent plain text.
    plain = html.unescape(re.sub(r"</?(?:pre|b)>", "", message))
    params = urllib.parse.urlencode({"phone": phone, "text": plain, "apikey": api_key})
    request = urllib.request.Request("https://api.callmebot.com/whatsapp.php?" + params)
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            body = response.read(2048).decode("utf-8", "replace")
            code = response.status
        # HTTP 200 alone is not always proof of WhatsApp acceptance.
        if code != 200 or re.search(r"error|invalid|not authorized|not allowed|limit exceeded", body, re.I):
            return False, "REJECTED", None
        return True, "ACCEPTED", None
    except Exception as exc:
        return False, "FAILED", type(exc).__name__


def _telegram_send(message):
    token, chat = credentials()
    if not token or not chat:
        return False, "UNCONFIGURED", None
    payload = urllib.parse.urlencode({"chat_id": chat, "text": message, "parse_mode": "HTML"}).encode()
    try:
        with urllib.request.urlopen(
            urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=payload),
            timeout=5,
        ) as response:
            result = json.load(response)
        if not result.get("ok"):
            return False, "REJECTED", None
        return True, "SENT", result.get("result", {}).get("message_id")
    except Exception as exc:
        return False, "FAILED", type(exc).__name__


def notification_mode():
    """Read persistent channel selection on each send; default preserves Telegram."""
    try:
        settings = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        mode = str(settings.get("channel", "TGR")).upper()
        return mode if mode in {"TGR", "WSP"} else "TGR"
    except (OSError, ValueError, TypeError):
        return "TGR"


def send(state, key, category, message):
    """Deliver independently; a failed channel never prevents the other."""
    sent = state.setdefault("sent", {})
    channels = state.setdefault("channel_sent", {})
    # Pre-upgrade Telegram deduplication records must remain valid.
    if key in sent and key not in channels:
        channels[key] = {"telegram": sent[key]}
    delivered = channels.setdefault(key, {})
    mode = notification_mode()
    targets = {"TGR": ["telegram"], "WSP": ["whatsapp"]}[mode]
    all_ok = True
    for channel in targets:
        if channel in delivered:
            continue
        if channel == "telegram":
            ok, status, detail = _telegram_send(message)
        else:
            ok, status, detail = _whatsapp_send(message)
        record = {"time": now().isoformat(), "key": key, "category": category,
                  "channel": channel, "status": status}
        if channel == "telegram" and ok:
            record["telegram_message_id"] = detail
        elif detail:
            record["error"] = detail
        write_jsonl(LOG_PATH, record)
        if ok:
            delivered[channel] = now().isoformat()
            if channel == "telegram":
                sent[key] = delivered[channel]
            save(state)
        else:
            all_ok = False
    return all_ok


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


def daily_peak_investment(rows):
    """Peak simultaneous cost basis reconstructed from open and closed lots."""
    if not isinstance(rows, list):
        return None
    events = []
    today = now().date()
    for row in rows:
        if not isinstance(row, dict):
            return None
        qty, price = safe_number(row.get("Qty")), safe_number(row.get("Buy_Prc"))
        if qty is None or price is None or qty <= 0 or price <= 0:
            return None
        try:
            bought = datetime.fromisoformat(str(row["Buy_Time"]))
        except (KeyError, TypeError, ValueError):
            return None
        if bought.date() != today:
            return None  # Carry-forward needs a separate opening-capital baseline.
        amount = qty * price
        events.append((bought, 1, amount))
        status = str(row.get("Status", "")).upper()
        if status == "CLOSED":
            try:
                exited = datetime.fromisoformat(str(row["Exit_Time"]))
            except (KeyError, TypeError, ValueError):
                return None
            if exited < bought:
                return None
            events.append((exited, 0, -amount))
        elif status != "OPEN":
            return None
    invested = peak = 0.0
    for _, _, change in sorted(events):
        invested += change
        if invested < -0.01:
            return None
        peak = max(peak, invested)
    return peak


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
    books = len({str(r.get("Cycle_ID", r.get("Book_ID"))) for r in closed if r.get("Book_ID") is not None}) if isinstance(trades, list) else None
    values = [safe_number(r.get("PNL")) for r in closed]
    closed_pnl = sum(values) if isinstance(trades, list) and all(v is not None for v in values) else None
    net = closed_pnl + open_pnl if closed_pnl is not None and open_pnl is not None else None
    peak = daily_peak_investment(trades)
    daily_return = (100 * net / peak) if net is not None and peak is not None and peak > 0 else None
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
            lines += [field("PnL %" if title == "AIRBORNE" else "Return %", f"{daily_return:+.2f}%" if daily_return is not None else "NA")]
        if title == "TOUCHDOWN":
            wins = sum(1 for r in closed if (safe_number(r.get("PNL")) or 0) > 0)
            losses = sum(1 for r in closed if (safe_number(r.get("PNL")) or 0) < 0)
            lines += [field("Wins", wins if books is not None else "NA"),
                      field("Losses", losses if books is not None else "NA")]
    if title == "TOUCHDOWN":
        lines.append(field("Peak Inv", money(peak)))
    lines += [field("Cycles", f"{books} Closed" if books is not None else "NA"),
              field("Errors", f"{errors} Reported"),
              field("Warnings", f"{warnings} Reported"),
              "━━━━━━━━━━━━━━━━━━━━━━━━",
              field("Status", status)]
    if title == "TOUCHDOWN":
        lines += ["━━━━━━━━━━━━━━━━━━━━━━━━", f"<b>🏆 FINAL NET PNL: {html.escape(money(net))} ({f'{daily_return:+.2f}%' if daily_return is not None else 'NA'})</b>"]
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
        book = row.get("Cycle_ID", row.get("Book_ID"))
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
        values = [safe_number(r.get("PNL")) for r in rows]
        pnl = sum(values) if all(v is not None for v in values) else None
        peak = daily_peak_investment(rows)
        book_return = (100 * pnl / peak) if pnl is not None and peak is not None and peak > 0 else None
        times = [str(r.get("Exit_Time", "")) for r in rows if r.get("Exit_Time")]
        exit_time = max(times) if times else "NA"
        lines = [
            f"📕 PXY — CYCLE #{html.escape(book)} CLOSED",
            "━━━━━━━━━━━━━━━━━━━━━━━━",
            field("Exit", exit_time),
            field("Peak Inv", money(peak)),
            field("Closed PnL", money(pnl)),
            field("Return %", f"{book_return:+.2f}%" if book_return is not None else "NA"),
            field("Status", "COMPLETED"),
            "━━━━━━━━━━━━━━━━━━━━━━━━",
        ]
        message = "\n".join(lines[:1]) + "\n<pre>" + "\n".join(lines[1:]) + "</pre>\n<b>🏆 CYCLE NET PNL: " + html.escape(money(pnl)) + " (" + (f"{book_return:+.2f}%" if book_return is not None else "NA") + ")</b>"
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


def event_message(kind, issue, stamp):
    recovered = kind == "RECOVERY"
    label = "🟢 PXY — EVENT RECOVERED" if recovered else "🚨 PXY — EVENT ALERT"
    greeting = "Good News! ✅" if recovered else "Attention Required! ⚠️"
    first = datetime.fromisoformat(issue["first"])
    duration = max(0, int((stamp - first).total_seconds()))
    severity = issue.get("severity", "ERROR")
    component = issue.get("component", "UNKNOWN")
    details = issue.get("detail", "NA")
    lines = [
        field("Date", stamp.strftime("%d-%b-%Y")),
        field("Time", stamp.strftime("%H:%M:%S")),
        field("Severity", severity),
        field("Component", component),
        field("Event", "RECOVERED" if recovered else "EXECUTION FAILURE" if severity == "ERROR" else "WARNING"),
        field("Duration", f"{duration // 3600:02d}:{duration // 60 % 60:02d}:{duration % 60:02d}"),
        field("Count", issue.get("count", 1)),
        field("Engine", "RUNNING" if engine_alive() else "STOPPED"),
        field("Trading", "NOT CONTROLLED"),
        field("Action", "NONE" if recovered else "MONITOR ONLY"),
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        field("Status", "RECOVERED" if recovered else "ACTIVE"),
    ]
    result = f"Hello {html.escape(socket.gethostname())}, {greeting}\n\n{label}\n<pre>" + "\n".join(lines) + "</pre>"
    if not recovered:
        result += "\n<b>Error Details</b>\n" + html.escape(details[:350])
    return result


def scan_events(state):
    stamp = now()
    minutes = stamp.hour * 60 + stamp.minute
    enabled = minutes < EVENT_WINDOW[1] or state.get("events_enabled", False)
    for line in capture_lines(state):
        if not PATTERN.search(line):
            continue
        # Normalize varying numeric details so repeated incidents share one key.
        signature = re.sub(r"\d+", "#", line)[:100]
        severity = "WARNING" if re.search(r"warning|stale", line, re.I) and not re.search(r"error|failed|failure|exception|traceback|critical", line, re.I) else "ERROR"
        component_match = re.search(r"[\w-]+\.py", line)
        component = component_match.group(0) if component_match else "UNKNOWN"
        issue = state.setdefault("issues", {}).get(signature)
        if issue is None:
            issue = {"first": stamp.isoformat(), "last": stamp.isoformat(), "alerted": False,
                     "severity": severity, "component": component, "detail": line[:350], "count": 0}
            state["issues"][signature] = issue
            daily = state.setdefault("daily_incidents", {}).setdefault(stamp.date().isoformat(), {"ERROR": 0, "WARNING": 0})
            daily[severity] = daily.get(severity, 0) + 1
        issue["last"] = stamp.isoformat()
        issue["count"] = issue.get("count", 0) + 1
        write_jsonl(EVENT_PATH, {"time": stamp.isoformat(), "signature": signature, "status": "OBSERVED"})
    for key, issue in list(state.setdefault("issues", {}).items()):
        first = datetime.fromisoformat(issue["first"])
        last = datetime.fromisoformat(issue["last"])
        age = (stamp - first).total_seconds()
        if age >= 120 and enabled and not issue["alerted"]:
            if send(state, f"event:{stamp.date()}:{key}:{issue['first']}", "EVENT", event_message("ALERT", issue, stamp)):
                issue["alerted"] = True
        # Silence is not confirmation of recovery. Keep incident open, with
        # no fabricated RECOVERED notification until positive evidence exists.
        if (stamp - last).total_seconds() > 3600 and not issue["alerted"]:
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
                state["daily_incidents"] = {last_date: {"ERROR": 0, "WARNING": 0}}
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
