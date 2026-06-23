"""End-to-end tests for the review-tool controls, driving the real page with a browser.

Starts the actual FastAPI app in-process and uses Playwright to click the real widgets and
assert their behaviour -- the only honest way to test the vanilla-JS controls. None of these
tests write corrections (they check DOM/state, not persistence), so the corpus is untouched.

Run: conda run -n atr-contributor python -m pytest contributor/tests/test_ui.py -q
(needs `playwright install chromium`).
"""

import threading
import time

import httpx
import pytest
import uvicorn

from atr_contributor.app import create_app

PORT = 8771
VOL1 = "saito-traditional-aikido-vol1"


@pytest.fixture(scope="session")
def server():
    srv = uvicorn.Server(uvicorn.Config(create_app("person:uitest", "UI Test"),
                                        host="127.0.0.1", port=PORT, log_level="warning"))
    th = threading.Thread(target=srv.run, daemon=True)
    th.start()
    base = f"http://127.0.0.1:{PORT}"
    for _ in range(150):
        try:
            if httpx.get(base + "/healthz", timeout=0.5).status_code == 200:
                break
        except Exception:
            pass
        time.sleep(0.1)
    else:
        raise RuntimeError("server did not start")
    yield base
    srv.should_exit = True
    th.join(timeout=5)


def open_page(pw, base, n):
    """Navigate to a specific pdf page, robust against a background image-index reload.
    NB: BOOKS/PAGE/page/book are `let` globals -> reference them bare, not via window.*"""
    pw.goto(base + "/")
    pw.wait_for_function("typeof BOOKS !== 'undefined' && BOOKS.length > 0", timeout=20000)
    pw.wait_for_function(
        f"""(() => {{
            if (PAGE && PAGE.page === {n} && document.querySelector('#cards .card, #cards .empty')) return true;
            book = '{VOL1}'; page = {n}; loadPage();
            return false;
        }})()""",
        timeout=30000, polling=600)


def test_boots_without_console_errors(server, page):
    errors = []
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(str(e)))
    open_page(page, server, 26)
    assert errors == [], errors


def test_sequence_nav_advances_on_multi_sequence_page(server, page):
    open_page(page, server, 28)                       # p28 has two sequences
    n = page.locator("#cards .card").count()
    assert n >= 2, f"expected >=2 sequences on p28, got {n}"
    assert page.locator("#snum").inner_text() == f"1/{n}"
    assert page.locator("#sprev").is_disabled()
    page.click("#snext")
    assert page.locator("#snum").inner_text() == f"2/{n}"
    assert page.locator("#sprev").is_disabled() is False
    page.click("#sprev")
    assert page.locator("#snum").inner_text() == f"1/{n}"


def test_sequence_nav_disabled_on_single_sequence_page(server, page):
    open_page(page, server, 26)                       # p26 has one sequence
    assert page.locator("#snum").inner_text() == "1/1"
    assert page.locator("#sprev").is_disabled()
    assert page.locator("#snext").is_disabled()


def test_content_nav_changes_page(server, page):
    open_page(page, server, 26)
    before = page.evaluate("page")
    page.click("#pnextc")
    page.wait_for_function(f"PAGE && PAGE.page > {before}", timeout=30000)
    assert page.evaluate("page") > before
    assert page.locator("#pagelabel").inner_text().startswith("Page")


def test_lock_button_toggles_and_moves_card_below(server, page):
    open_page(page, server, 28)
    page.locator("#cards .card").first.locator(".vL").click()
    assert "Unlock" in page.locator("#locked-card .vL").inner_text()
    assert page.locator("#locked #locked-card").count() == 1     # moved into the locked panel
    page.locator("#locked-card .vL").click()                     # unlock
    page.wait_for_selector("#cards .card")
    assert page.locator("#locked").inner_text().strip() == ""    # panel cleared


def test_save_button_dirty_state(server, page):
    open_page(page, server, 28)
    card = page.locator("#cards .card").first
    assert card.locator(".vK").is_disabled()           # nothing to save yet
    card.locator(".nr").fill("test edit")              # an edit dirties the card
    assert card.locator(".vK").is_disabled() is False  # now enabled


def test_textpanel_shows_captured_blocks(server, page):
    open_page(page, server, 28)
    page.wait_for_selector("#tblocks .tblock", timeout=10000)
    assert page.locator("#tblocks .tblock").count() >= 1
