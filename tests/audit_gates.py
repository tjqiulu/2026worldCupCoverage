"""8-gate audit for the user's exact bug scenario.

Gates:
G1: Server responds to /api/health
G2: /api/matches returns 104 matches with details
G3: USA vs Paraguay details present with score 4-1
G4: Goalscorers include all 5 with correct minutes (7, 31, 45+5, 90+8, 73)
G5: OG type assigned to Bobadilla
G6: Page loads without console errors
G7: Modal opens for USA vs Paraguay
G8: Modal shows score 4-1 + all 5 goals with stoppage time
"""
import json
import sys
import urllib.request
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8766"
failures = []

def gate(name, fn):
    try:
        result = fn()
        if result is True:
            print(f"  ✅ {name}")
        else:
            print(f"  ❌ {name}: {result}")
            failures.append(name)
    except Exception as e:
        print(f"  ❌ {name}: EXCEPTION {e}")
        failures.append(name)

print("=" * 60)
print("Plan 016 follow-up: 8-gate audit")
print("=" * 60)

# G1
def g1():
    with urllib.request.urlopen(f"{BASE}/api/health", timeout=5) as r:
        return r.status == 200
gate("G1: /api/health 200", g1)

# G2
def g2():
    with urllib.request.urlopen(f"{BASE}/api/matches", timeout=5) as r:
        data = json.loads(r.read())
        return len(data) == 104 or f"got {len(data)}"
gate("G2: /api/matches returns 104 matches", g2)

# G3
def g3():
    with urllib.request.urlopen(f"{BASE}/api/matches", timeout=5) as r:
        data = json.loads(r.read())
    usa = next((m for m in data if m.get("home", {}).get("name") == "USA" and m.get("away", {}).get("name") == "Paraguay"), None)
    if not usa:
        return "USA vs Paraguay match not in data"
    d = usa.get("details")
    if not d:
        return f"details is None"
    if d["score"] != {"home": 4, "away": 1}:
        return f"score is {d['score']}, expected 4-1"
    return True
gate("G3: USA 4-1 Paraguay details present", g3)

# G4
def g4():
    with urllib.request.urlopen(f"{BASE}/api/matches", timeout=5) as r:
        data = json.loads(r.read())
    usa = next((m for m in data if m.get("home", {}).get("name") == "USA"), None)
    goals = usa["details"]["goalscorers"]
    expected = [
        ("D. Bobadilla", 7, None, "own_goal"),
        ("F. Balogun", 31, None, None),
        ("F. Balogun", 45, 5, None),
        ("G. Reyna", 90, 8, None),
        ("Maurício", 73, None, None),
    ]
    actual = [(g["player"], g["minute"], g.get("stoppage"), g.get("type")) for g in goals]
    return f"actual={actual}, expected={expected}" if actual != expected else True
gate("G4: All 5 goals with correct minutes/stoppage/types", g4)

# G5
def g5():
    with urllib.request.urlopen(f"{BASE}/api/matches", timeout=5) as r:
        data = json.loads(r.read())
    usa = next((m for m in data if m.get("home", {}).get("name") == "USA"), None)
    bobadilla = next((g for g in usa["details"]["goalscorers"] if g["player"] == "D. Bobadilla"), None)
    return f"type={bobadilla.get('type')}" if not bobadilla or bobadilla.get("type") != "own_goal" else True
gate("G5: Bobadilla marked as own_goal", g5)

# G6, G7, G8 - use Playwright
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
    context = browser.new_context(viewport={"width": 1280, "height": 800})
    page = context.new_page()
    errors = []
    page.on("console", lambda m: errors.append(f"{m.type}: {m.text}") if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))

    def g6():
        page.goto(BASE, wait_until="networkidle", timeout=15000)
        page.wait_for_timeout(2000)
        return True if not errors else f"errors: {errors}"
    gate("G6: Page loads with no console errors", g6)

    def g7():
        # Click USA match
        page.click('button.tab[data-tab="matches"]')
        page.wait_for_selector('#matches-view.active .match-card', timeout=10_000)
        target = page.evaluate("() => allMatches.find(m => m.home.name === 'USA' && m.away.name === 'Paraguay').match_id")
        page.click(f'[data-id="{target}"]')
        page.wait_for_selector('#match-modal:not([hidden])', timeout=5_000)
        page.wait_for_timeout(1500)
        return True
    gate("G7: Modal opens for USA vs Paraguay", g7)

    def g8():
        # Check the score and goals are visible
        score_text = page.locator('.modal-score-big').text_content()
        if "4" not in score_text or "1" not in score_text:
            return f"score text: {score_text!r}"
        # Check goals section has 5 rows
        goals = page.locator('.goal-row').count()
        if goals != 5:
            return f"got {goals} goals, expected 5"
        # Check stoppage times
        page_text = page.locator('.modal-goals-list').text_content()
        for needle in ("45'+5'", "90'+8'", "OG", "Bobadilla", "Balogun", "Reyna", "Maurício"):
            if needle not in page_text:
                return f"missing: {needle!r}"
        # Take screenshot for record
        page.locator('#match-modal .match-modal-card').screenshot(path='tests/e2e/screenshots/audit_g8_usa_para.png')
        return True
    gate("G8: Modal shows 4-1 + 5 goals with stoppage time", g8)

    browser.close()

print()
print("=" * 60)
if failures:
    print(f"❌ {len(failures)} gates FAILED: {failures}")
    sys.exit(1)
else:
    print("✅ All 8 gates passed. Safe to claim done.")
    sys.exit(0)
