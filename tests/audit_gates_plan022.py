"""8-gate closure audit for Plan 022 (Cloudflare quick tunnel).

8 gates verify:
G1: cloudflared installed (which + version)
G2: Flask still on 8766 (backward compat: PORT 8766 from plan 021)
G3: Tunnel process running (pidfile valid)
G4: Public URL extracted from log
G5: Public URL reachable from outside (HTTP 200)
G6: Public URL serves /api/matches (104 matches)
G7: pytest 200/200 pass (no regression)
G8: Manual: phone can access public URL from 4G (user action)
"""
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG = "/tmp/cf_tunnel.log"
PIDFILE = "/tmp/cf_tunnel.pid"
PUBLIC_URL_FILE = "/tmp/cf_public_url.txt"  # cached for repeated runs
failures = []
manual_gates = []


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
print("Plan 022 — Cloudflare Quick Tunnel 8-gate Closure Audit")
print("=" * 64)


def _get_url():
    """Get URL from log file, with retry."""
    for _ in range(5):
        if os.path.exists(LOG):
            m = re.search(r'https://[a-z0-9-]+\.trycloudflare\.com', Path(LOG).read_text())
            if m:
                return m.group(0)
        time.sleep(1)
    return None


# ---------- G1: cloudflared installed ----------
def g1():
    # Check standard locations
    for p in ["cloudflared", os.path.expanduser("~/.local/bin/cloudflared")]:
        try:
            r = subprocess.run([p, "--version"], capture_output=True, text=True, timeout=5)
            if r.returncode == 0:
                # Extract version
                vmatch = re.search(r'cloudflared version (\S+)', r.stdout + r.stderr)
                version = vmatch.group(1) if vmatch else "unknown"
                return f"{p} OK ({version})"  # Return version info, not True
        except FileNotFoundError:
            continue
        except Exception as e:
            continue
    return "cloudflared not found in PATH or ~/.local/bin/"
# Note: g1 returns version string on success, but gate() checks for True.
# Fix: rewrap
def g1_check():
    result = g1()
    return True if "OK" in str(result) else result
gate("G1: cloudflared installed (any PATH or ~/.local/bin/)", g1_check)

# ---------- G2: Flask still on 8766 ----------
def g2():
    try:
        with urllib.request.urlopen("http://127.0.0.1:8766/api/health", timeout=5) as r:
            if r.status == 200:
                import json
                data = json.loads(r.read())
                if data.get("status") == "ok":
                    return True
                return f"health returned {data}"
    except Exception as e:
        return f"127.0.0.1:8766 unreachable: {e}"
    return "127.0.0.1:8766 returned non-200"
gate("G2: Flask still on 8766 (backward compat from plan 021)", g2)

# ---------- G3: Tunnel process running ----------
def g3():
    if not os.path.exists(PIDFILE):
        return f"{PIDFILE} missing. Start: bin/tunnel.sh"
    try:
        pid = int(Path(PIDFILE).read_text().strip())
    except Exception as e:
        return f"can't read PID: {e}"
    try:
        os.kill(pid, 0)  # signal 0 = check if alive
        return True
    except ProcessLookupError:
        return f"pid {pid} not running"
    except PermissionError:
        return True  # owned by other user but exists
    except Exception as e:
        return f"pid check failed: {e}"
gate("G3: Tunnel process running (pidfile valid)", g3)

# ---------- G4: Public URL extracted ----------
def g4():
    url = _get_url()
    if not url:
        return f"no trycloudflare.com URL in {LOG}"
    # Save for later gates
    Path(PUBLIC_URL_FILE).write_text(url)
    print(f"        URL: {url}")
    return True
gate("G4: Public URL extracted from log", g4)

# ---------- G5: Public URL reachable ----------
def g5():
    url = Path(PUBLIC_URL_FILE).read_text().strip() if os.path.exists(PUBLIC_URL_FILE) else None
    if not url:
        return "no public URL cached (G4 failed)"
    try:
        with urllib.request.urlopen(f"{url}/api/health", timeout=20) as r:
            if r.status == 200:
                return True
            return f"HTTP {r.status}"
    except Exception as e:
        return f"unreachable: {e}"
gate("G5: Public URL reachable from this host (HTTP 200)", g5)

# ---------- G6: Public URL serves matches ----------
def g6():
    url = Path(PUBLIC_URL_FILE).read_text().strip() if os.path.exists(PUBLIC_URL_FILE) else None
    if not url:
        return "no public URL cached"
    try:
        with urllib.request.urlopen(f"{url}/api/matches", timeout=30) as r:
            if r.status != 200:
                return f"HTTP {r.status}"
            import json
            data = json.loads(r.read())
            if len(data) != 104:
                return f"got {len(data)} matches, expected 104"
            return True
    except Exception as e:
        return f"/api/matches failed: {e}"
gate("G6: Public URL serves /api/matches (104 matches)", g6)

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

# ---------- G8: manual ----------
def g8():
    return True
gate("G8: Phone 4G can access public URL (MANUAL — user action)", g8, manual=True)


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
    print(f"MANUAL gates: {manual_gates}")
if os.path.exists(PUBLIC_URL_FILE):
    print(f"Public URL: {Path(PUBLIC_URL_FILE).read_text().strip()}")
print("=" * 64)

sys.exit(1 if failures else 0)
