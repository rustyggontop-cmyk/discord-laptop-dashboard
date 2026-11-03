"""Private dashboard for the Shardnote Debian laptop.

Run this on the laptop, not GitHub Pages. All secrets live in .env.
"""
import json
import os
import platform
import secrets
import socket
import subprocess
import time
from datetime import timedelta
from functools import wraps

import psutil
from dotenv import load_dotenv
from flask import Flask, Response, abort, jsonify, redirect, render_template, request, session, stream_with_context, url_for
from werkzeug.security import check_password_hash

load_dotenv()

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("FLASK_SECRET_KEY"),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE", "true").lower() == "true",
    SESSION_COOKIE_SAMESITE="Lax",
    PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
)

PASSWORD_HASH = os.environ.get("DASHBOARD_PASSWORD_HASH")
if not app.config["SECRET_KEY"] or not PASSWORD_HASH:
    raise RuntimeError("Set FLASK_SECRET_KEY and DASHBOARD_PASSWORD_HASH in .env")

START_TIME = psutil.boot_time()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("authenticated"):
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def csrf_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if request.headers.get("X-CSRF-Token") != session.get("csrf_token"):
            abort(403)
        return view(*args, **kwargs)
    return wrapped


def format_bytes(value):
    return f"{value / 1024 ** 3:.1f} GB"


def battery():
    value = psutil.sensors_battery()
    if value is None:
        return {"available": False}
    if value.secsleft in (psutil.POWER_TIME_UNKNOWN, psutil.POWER_TIME_UNLIMITED):
        remaining = "Unknown"
    else:
        remaining = str(timedelta(seconds=max(0, int(value.secsleft))))
    return {
        "available": True,
        "percent": round(value.percent),
        "charging": bool(value.power_plugged),
        "remaining": remaining,
    }


def service_active(name):
    result = subprocess.run(
        ["systemctl", "is-active", name], capture_output=True, text=True, check=False
    )
    return result.stdout.strip() == "active"


def temperature_readings():
    readings = []
    try:
        for sensor, values in psutil.sensors_temperatures().items():
            device = "CPU" if sensor.startswith("coretemp") else "Wi-Fi" if sensor.startswith("iwlwifi") else "NVMe SSD" if sensor.startswith("nvme") else sensor
            for value in values:
                if value.current is not None:
                    readings.append({"device": device, "label": value.label or device, "current": round(value.current, 1)})
    except (AttributeError, OSError):
        pass
    return readings


def system_stats():
    memory = psutil.virtual_memory()
    swap = psutil.swap_memory()
    disk = psutil.disk_usage("/")
    try:
        load = list(os.getloadavg())
    except (AttributeError, OSError):
        load = [0, 0, 0]
    return {
        "host": socket.gethostname(),
        "os": platform.freedesktop_os_release().get("PRETTY_NAME", "Debian"),
        "kernel": platform.release(),
        "architecture": platform.machine(),
        "python": platform.python_version(),
        "uptime": str(timedelta(seconds=int(time.time() - START_TIME))),
        "cpu": round(psutil.cpu_percent(interval=None), 1),
        "physical_cores": psutil.cpu_count(logical=False) or 0,
        "cores": psutil.cpu_count(logical=True) or 0,
        "load": [round(item, 2) for item in load],
        "memory": {"percent": round(memory.percent, 1), "used": format_bytes(memory.used), "total": format_bytes(memory.total)},
        "swap": {"percent": round(swap.percent, 1), "used": format_bytes(swap.used), "total": format_bytes(swap.total)},
        "disk": {"percent": round(disk.percent, 1), "used": format_bytes(disk.used), "total": format_bytes(disk.total)},
        "battery": battery(),
        "temperatures": temperature_readings(),
        "bot_online": service_active(os.environ.get("BOT_SERVICE", "shardnote-bot.service")),
    }


@app.route("/")
def home():
    return redirect(url_for("dashboard") if session.get("authenticated") else url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        password = request.form.get("password", "")
        if check_password_hash(PASSWORD_HASH, password):
            session.clear()
            session["authenticated"] = True
            session["csrf_token"] = secrets.token_urlsafe(32)
            session.permanent = True
            return redirect(url_for("dashboard"))
        error = "Wrong password. Try again."
    return render_template("login.html", error=error)


@app.post("/logout")
@login_required
@csrf_required
def logout():
    session.clear()
    return jsonify(ok=True)


@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", stats=system_stats(), csrf_token=session["csrf_token"])


@app.get("/api/status")
@login_required
def status():
    return jsonify(system_stats())


@app.get("/api/events")
@login_required
def events():
    """Push fresh laptop status to the open dashboard once per second."""
    @stream_with_context
    def generate():
        while True:
            yield f"data: {json.dumps(system_stats())}\n\n"
            time.sleep(1)

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def perform_system_action(action):
    # This needs a narrow sudoers allow-rule documented in README.md.
    subprocess.Popen(["sudo", "-n", "/usr/bin/systemctl", action])


@app.post("/api/power/<action>")
@login_required
@csrf_required
def power(action):
    if action not in {"reboot", "poweroff"}:
        abort(404)
    body = request.get_json(silent=True) or {}
    if body.get("confirm") != action:
        return jsonify(error="Confirmation did not match."), 400
    perform_system_action(action)
    return jsonify(ok=True, message=f"{action.title()} command sent.")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8123, debug=False)

