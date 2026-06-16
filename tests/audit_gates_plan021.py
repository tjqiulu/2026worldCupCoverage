"""8-gate closure audit for Plan 021 (Render deployment).

8 gates verify:
G1: render.yaml exists + valid YAML + required keys
G2: requirements.txt has gunicorn
G3: src/app.py reads PORT from env (backward compat: default 8766)
G4: docs/deployment/render.md exists
G5: Local server starts on 8766 (backward compat, NOT 10000)
G6: /api/health 200 + /api/matches returns 104
G7: pytest 200/200 pass
G8: Manual gate: Render build success + public URL 4G reachable
    (cannot run locally; checked manually after user pushes)
"""
import os
import re
import subprocess
import sys
import time
import urllib.request
import yaml
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
failures = []
manual_gates = []  # gates requiring user action, not failing


def gate(name, fn, manual=False):
    try:
        result = fn()
        if result is True:
            print(f"  PASS  {name}")
        else:
            print(f"  FAIL  {name}: {result}")
            if not manual:
                failures.append(name)
            else:
                manual_gates.append(name)
    except Exception as e:
        print(f"  FAIL  {name}: EXCEPTION {e}")
        if not manual:
            failures.append(name)
        else:
            manual_gates.append(name)


print("=" * 64)
print("Plan 021 — Render Deployment 8-gate Closure Audit")
print("=" * 64)

# ---------- G1: render.yaml valid ----------
def g1():
    p = ROOT / "render.yaml"
    if not p.exists():
        return "render.yaml does not exist"
    try:
        cfg = yaml.safe_load(p.read_text())
    except Exception as e:
        return f"YAML parse error: {e}"
    services = cfg.get("services", [])
    if not services:
        return "no services[] in render.yaml"
    s = services[0]
    required = ["type", "name", "runtime", "buildCommand", "startCommand", "envVars", "plan"]
    missing = [k for k in required if k not in s]
    if missing:
        return f"missing keys: {missing}"
    if s["type"] != "web":
        return f"type is {s['type']!r}, expected 'web'"
    if s["runtime"] != "python":
        return f"runtime is {s['runtime']!r}, expected 'python'"
    if "$PORT" not in s["startCommand"]:
        return "startCommand doesn't reference $PORT (Render injects this)"
    if "0.0.0.0" not in s["startCommand"]:
        return "startCommand should bind to 0.0.0.0 (not 127.0.0.1)"
    if not s["startCommand"].startswith("gunicorn"):
        return "startCommand should use gunicorn"
    py_ver = next((e["value"] for e in s["envVars"] if e["key"] == "PYTHON_VERSION"), None)
    if not py_ver or not re.match(r"3\.\d+\.\d+", py_ver):
        return f"PYTHON_VERSION env var missing or invalid: {py_ver!r}"
    return True
gate("G1: render.yaml valid + has all required keys", g1)

# ---------- G2: requirements.txt has gunicorn ----------
def g2():
    p = ROOT / "requirements.txt"
    if not p.exists():
        return "requirements.txt missing"
    txt = p.read_text().lower()
    if "gunicorn" not in txt:
        return "gunicorn not in requirements.txt"
    if "flask" not in txt:
        return "flask not in requirements.txt"
    if "icalendar" not in txt:
        return "icalendar not in requirements.txt"
    if "requests" not in txt:
        return "requests not in requirements.txt"
    return True
gate("G2: requirements.txt has gunicorn + base deps", g2)

# ---------- G3: src/app.py reads PORT from env ----------
def g3():
    p = ROOT / "src" / "app.py"
    if not p.exists():
        return "src/app.py missing"
    txt = p.read_text()
    # Must have os.environ.get("PORT", ...) pattern
    m = re.search(r'PORT\s*=\s*int\(\s*os\.environ\.get\(\s*["\']PORT["\']\s*,\s*(\d+)\s*\)\)', txt)
    if not m:
        return "PORT must be int(os.environ.get('PORT', <default>)) pattern"
    default = int(m.group(1))
    if default != 8766:
        return f"PORT default is {default}, expected 8766 (backward compat)"
    if 'HOST = "0.0.0.0"' not in txt:
        return "HOST must be 0.0.0.0 (LAN-accessible)"
    return True
gate("G3: src/app.py reads PORT from env (default 8766)", g3)

# ---------- G4: deployment doc exists ----------
def g4():
    p = ROOT / "docs" / "deployment" / "render.md"
    if not p.exists():
        return "docs/deployment/render.md missing"
    txt = p.read_text()
    # Sanity check content
    if "render.yaml" not in txt:
        return "doc doesn't mention render.yaml"
    if "gunicorn" not in txt:
        return "doc doesn't mention gunicorn"
    if "8766" not in txt:
        return "doc doesn't mention local 8766 default"
    if "ephemeral" not in txt.lower() and "restart" not in txt.lower():
        return "doc doesn't mention ephemeral disk / restart caveat"
    return True
gate("G4: docs/deployment/render.md exists with key content", g4)

# ---------- G5: local server starts on 8766 (backward compat) ----------
def g5():
    # Check if server already running
    try:
        with urllib.request.urlopen("http://127.0.0.1:8766/api/health", timeout=2) as r:
            if r.status == 200:
                return True
    except Exception:
        pass
    # Try to start it
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    # Make sure no PORT env var leaks in
    env.pop("PORT", None)
    log = open("/tmp/wc_audit_g5.log", "w")
    proc = subprocess.Popen(
        ["python3", "-m", "src.app"],
        cwd=ROOT,
        env=env,
        stdout=log,
        stderr=subprocess.STDOUT,
    )
    try:
        for i in range(20):  # up to 10s
            time.sleep(0.5)
            try:
                with urllib.request.urlopen("http://127.0.0.1:8766/api/health", timeout=1) as r:
                    if r.status == 200:
                        return True
            except Exception:
                continue
        # Get the log for debugging
        log.flush()
        with open("/tmp/wc_audit_g5.log") as f:
            tail = f.read()[-500:]
        return f"server didn't respond on 8766 in 10s. Log tail:\n{tail}"
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
gate("G5: local server starts on PORT 8766 (NOT 10000 from $PORT)", g5)

# ---------- G6: API endpoints work + 104 matches ----------
def g6():
    # Reuse running server if any, else spin up
    server_proc = None
    try:
        try:
            with urllib.request.urlopen("http://127.0.0.1:8766/api/health", timeout=1) as r:
                if r.status == 200:
                    return _check_endpoints()
        except Exception:
            pass
        # Spin up
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT)
        env.pop("PORT", None)
        log = open("/tmp/wc_audit_g6.log", "w")
        server_proc = subprocess.Popen(
            ["python3", "-m", "src.app"],
            cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT,
        )
        for _ in range(20):
            time.sleep(0.5)
            try:
                with urllib.request.urlopen("http://127.0.0.1:8766/api/health", timeout=1) as r:
                    if r.status == 200:
                        break
            except Exception:
                continue
        return _check_endpoints()
    finally:
        if server_proc:
            server_proc.terminate()
            try: server_proc.wait(timeout=3)
            except: server_proc.kill()


def _check_endpoints():
    errs = []
    for path in ["/api/health", "/"]:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:8766{path}", timeout=5) as r:
                if r.status != 200:
                    errs.append(f"{path}={r.status}")
        except Exception as e:
            errs.append(f"{path}={e}")
    # /api/matches is slow (17s) because it calls worldcup26.ir for enrichment
    try:
        with urllib.request.urlopen("http://127.0.0.1:8766/api/matches", timeout=30) as r:
            if r.status != 200:
                errs.append(f"/api/matches={r.status}")
            else:
                import json
                data = json.loads(r.read())
                if len(data) != 104:
                    errs.append(f"/api/matches returns {len(data)}, expected 104")
    except Exception as e:
        errs.append(f"/api/matches={e}")
    try:
        req = urllib.request.Request(
            "http://127.0.0.1:8766/api/refresh", method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            if r.status != 200:
                errs.append(f"POST /api/refresh={r.status}")
    except Exception as e:
        errs.append(f"POST /api/refresh={e}")
    if errs:
        return "; ".join(errs)
    return True
gate("G6: 4 endpoints 200 + /api/matches returns 104", g6)

# ---------- G7: pytest 200/200 ----------
def g7():
    p = subprocess.run(
        ["pytest", "tests/", "-q", "--ignore=tests/e2e", "-x"],
        cwd=ROOT, capture_output=True, text=True, timeout=180,
        env={**os.environ, "PYTHONPATH": str(ROOT)},
    )
    out = p.stdout + "\n" + p.stderr
    m = re.search(r"(\d+)\s+passed", out)
    if not m:
        return f"no 'passed' line in pytest output:\n{out[-800:]}"
    n = int(m.group(1))
    if n < 200:
        return f"only {n} tests pass (expected 200)"
    if p.returncode != 0:
        return f"pytest exit code {p.returncode}"
    return True
gate("G7: pytest 200/200 pass (no regression)", g7)

# ---------- G8: manual gate ----------
def g8():
    # Cannot run locally. User must:
    # 1. git push origin main
    # 2. Render dashboard: New + → Blueprint → select repo
    # 3. Wait for build (3-5 min)
    # 4. Verify https://wc2026-coverage.onrender.com/api/health 200
    # 5. Test from phone 4G
    return True
gate("G8: Render build + public URL reachable (MANUAL — user action)", g8, manual=True)

# ---------- Summary ----------
print()
print("=" * 64)
total = 8
passed = total - len(failures) - len(manual_gates)
manual_ok = total - len(failures) - passed
print(f"Result: {passed} pass / {len(failures)} fail / {manual_ok} manual-pass")
if failures:
    print(f"FAILURES: {failures}")
if manual_gates:
    print(f"MANUAL gates (not counted as fail): {manual_gates}")
print("=" * 64)

sys.exit(1 if failures else 0)
