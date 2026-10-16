"""Real Chromium browser E2E for the SERA v0.9 offline reviewer UI.

This is NOT a human annotation: every change below is a synthetic UI action.
Verifies actual clicks, source-evidence capture, blocked fabricated quotes,
JSON download/import and Python validation, in both desktop and mobile sizes.

Requires 'pip install playwright' and 'python -m playwright install chromium'.
Run: python -m experiments.sera.browser_e2e_v09
"""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import json

from experiments.sera.sentence_review_packet_v07 import generate_mara_packet
from experiments.sera.review_forms_cli_v08 import validate_file
from experiments.sera.reviewer_ui_v09 import export_mara_browser_forms


def require(condition, reason):
    if not condition:
        raise AssertionError(reason)


def fill_known_entities(page):
    hints = page.locator("#entityList .entity")
    for i in range(hints.count()):
        hints.nth(i).locator("select").select_option("PHYSICALLY_PRESENT")
        hints.nth(i).locator("input").fill("Synthetic E2E annotation only")


def select_sentence(page, index):
    page.locator("#navigation button").nth(index).click()
    require(page.locator("#sentenceTitle").inner_text() ==
            f"Cümle {index+1} / 28", "Sentence navigation changed the wrong row")


def run_browser_e2e() -> dict:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("PLAYWRIGHT_MISSING_FOR_REAL_BROWSER_TEST") from exc

    packet = generate_mara_packet()
    rows = packet["sentences"]
    close_idx = next(
        i for i, row in enumerate(rows)
        if "closed the case" in row["quote"]
    )
    claim_idx = next(
        i for i, row in enumerate(rows)
        if "Arrival recorded: 02:10" in row["quote"]
    )

    with TemporaryDirectory(prefix="sera-browser-e2e-") as directory:
        base = Path(directory)
        page_dir = base / "html"
        export_mara_browser_forms(page_dir)
        output = base / "reviewer_A_export.json"
        reexport = base / "reviewer_A_reexport.json"
        errors = []
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                desktop = browser.new_context(
                    accept_downloads=True, viewport={"width": 1280, "height": 850}
                )
                try:
                    page = desktop.new_page()
                    page.on("pageerror", lambda err: errors.append(str(err)))
                    page.goto((page_dir / "reviewer_A_unverified.html").as_uri())
                    require("SERA Mara S1" in page.title(), "Browser page title missing")
                    require(page.locator("#navigation button").count() == 28,
                            "Browser did not render all 28 Mara sentences")
                    require(page.locator("#progress").inner_text() == "0/28",
                            "Blank human review was pre-marked complete")

                    select_sentence(page, close_idx)
                    source_quote = page.locator("#sentenceQuote").inner_text()
                    require("closed the case" in source_quote,
                            "Actual watch-close sentence not shown")
                    page.locator("#disposition").select_option("STATE_EVENT")
                    fill_known_entities(page)
                    page.locator("#rowNotes").fill(
                        "Synthetic QA: open watch case closes; no gold approval"
                    )

                    # Fabricated evidence MUST be blocked by the live UI.
                    page.locator("#eventId").fill("ev_case_close")
                    page.locator("#eventType").select_option("CLOSE")
                    page.locator("#eventEffect").select_option("OBJECT")
                    page.locator("#eventQuote").fill(
                        "the train definitely arrived physically"
                    )
                    page.locator("#eventReason").fill("Synthetic browser QA")
                    page.locator("#addEvent").click()
                    require(page.locator("#eventList .event").count() == 0,
                            "Fabricated event quote entered the review form")
                    require("geçerli" in page.locator("#statusText").inner_text(),
                            "Invalid quote did not show user-visible feedback")

                    # Source-grounded, lexicon-missed object.
                    page.locator("#extraRef").fill("new:watch_case")
                    page.locator("#extraQuote").fill("case")
                    page.locator("#extraDecision").select_option(
                        "PHYSICALLY_PRESENT"
                    )
                    page.locator("#extraReason").fill(
                        "Case is explicitly closed in source prose"
                    )
                    page.locator("#addExtraEntity").click()
                    require(page.locator("#extraEntityList .entity").count() == 1,
                            "Manual source-bound entity candidate not added")

                    page.locator("#eventQuote").fill("closed the case")
                    page.locator("#eventRefs").fill("vane,new:watch_case")
                    page.locator("#eventReason").fill(
                        "Actual case closure; unrelated to train arrival truth"
                    )
                    page.locator("#addEvent").click()
                    require(page.locator("#eventList .event").count() == 1,
                            "Verified quote did not create event annotation")
                    require(page.locator("#progress").inner_text() == "1/28",
                            "Reviewed source sentence progress incorrect")

                    # A reported train arrival MUST NOT become an objective
                    # world arrival simply because it is quoted in a record.
                    select_sentence(page, claim_idx)
                    page.locator("#disposition").select_option("CLAIM_ONLY")
                    fill_known_entities(page)
                    page.locator("#rowNotes").fill(
                        "Synthetic QA: a record says 02:10; no train arrival proven"
                    )
                    page.locator("#eventId").fill("ev_record_claim")
                    page.locator("#eventType").select_option("CLAIM_MENTION")
                    page.locator("#eventEpistemic").select_option(
                        "REPORTED_CLAIM"
                    )
                    page.locator("#eventEffect").select_option("NONE")
                    page.locator("#eventQuote").fill("Arrival recorded: 02:10")
                    page.locator("#eventReason").fill(
                        "Record assertion, not a physical occurrence"
                    )
                    page.locator("#addEvent").click()
                    require(page.locator("#eventList .event").count() == 1,
                            "Document claim annotation failed")

                    # Navigate away/back: in-browser source decisions persist.
                    select_sentence(page, close_idx)
                    require(page.locator("#eventList .event").count() == 1,
                            "Navigation silently lost a typed event")
                    require(page.locator("#extraEntityList .entity").count() == 1,
                            "Navigation silently lost a missing-object candidate")

                    with page.expect_download() as downloaded:
                        page.locator("#exportBtn").click()
                    downloaded.value.save_as(str(output))
                    raw = json.loads(output.read_text(encoding="utf-8"))
                    require(raw["gold_status"] == "NOT_GOLD",
                            "Browser forged a gold approval")
                    require(raw["canonical_commit_authorized"] is False,
                            "Browser attempted a canonical state commit")
                    require(raw["rows"][close_idx]["events"][0]["quote"] ==
                            "closed the case", "Export lost source quote")
                    require(raw["rows"][close_idx]["extra_entity_candidates"][0]
                            ["ref"] == "new:watch_case",
                            "Export lost manually discovered object")
                    require(raw["rows"][claim_idx]["events"][0]["epistemic"] ==
                            "REPORTED_CLAIM",
                            "Browser promoted claim into asserted truth")

                    validated = validate_file(review=output)
                    require(validated["reviewed_sentence_count"] == 2,
                            "Python review validator rejected synthetic UI evidence")
                    require(validated["gold_qualified"] is False,
                            "Offline validator falsely qualified human gold")
                    require(validated["unreviewed_sentence_ids"] and
                            validated["status"] == "PARTIAL_REVIEW_HOLD",
                            "A 2/28 source review should remain incomplete")

                    # Import on a new tab, with exact role, source, hints.
                    fresh = desktop.new_page()
                    fresh.on("pageerror",lambda err: errors.append(str(err)))
                    fresh.goto((page_dir / "reviewer_A_unverified.html").as_uri())
                    fresh.locator("#fileInput").set_input_files(str(output))
                    fresh.wait_for_function(
                        "() => document.getElementById('progress').textContent === '2/28'"
                    )
                    select_sentence(fresh, close_idx)
                    require(fresh.locator("#eventList .event").count() == 1,
                            "Imported JSON lost annotated event")
                    require(fresh.locator("#extraEntityList .entity").count() == 1,
                            "Imported JSON lost separately discovered object")
                    require("QA:" in fresh.locator("#rowNotes").input_value(),
                            "Imported JSON lost reviewer notes")
                    with fresh.expect_download() as roundtrip:
                        fresh.locator("#exportBtn").click()
                    roundtrip.value.save_as(str(reexport))
                    require(json.loads(reexport.read_text()) == raw,
                            "Export/import/export changed the review data")

                    # Independent reviewer B cannot import reviewer A's form.
                    b = desktop.new_page()
                    b.on("pageerror",lambda err: errors.append(str(err)))
                    b.goto((page_dir / "reviewer_B_unverified.html").as_uri())
                    b.locator("#fileInput").set_input_files(str(output))
                    require(b.locator("#progress").inner_text() == "0/28",
                            "Other reviewer imported a competing answer")
                    require("alınamadı" in b.locator("#statusText").inner_text(),
                            "Role mismatch did not show visible failure")

                    # Responsive/mobile navigation without a second source.
                    mobile = browser.new_context(
                        accept_downloads=True,
                        viewport={"width": 390, "height": 844},
                        is_mobile=True, has_touch=True
                    )
                    try:
                        mobile_page = mobile.new_page()
                        mobile_page.on("pageerror",
                                       lambda err: errors.append(str(err)))
                        mobile_page.goto(
                            (page_dir / "reviewer_B_unverified.html").as_uri()
                        )
                        require(mobile_page.locator("#navigation button").count()
                                == 28, "Mobile form lost source sentences")
                        mobile_page.locator("#navigation button").nth(close_idx).click()
                        require("closed the case" in
                                mobile_page.locator("#sentenceQuote").inner_text(),
                                "Mobile navigation failed")
                    finally:
                        mobile.close()
                finally:
                    desktop.close()
            finally:
                browser.close()
        require(not errors, "Browser JavaScript exception: " + "; ".join(errors))
        return {
            "schema": "sera.browser-e2e-result.v0.9",
            "browser": "chromium-headless",
            "sentence_count": len(rows),
            "synthetic_edited_sentences": 2,
            "unreviewed_sentences": 26,
            "source_bound_object_added": True,
            "fabricated_event_blocked": True,
            "source_claim_kept_reported": True,
            "download_python_validated": True,
            "json_roundtrip_exact": True,
            "cross_reviewer_import_blocked": True,
            "mobile_navigation_passed": True,
            "browser_javascript_errors": len(errors),
            "real_human_reviews_performed": 0,
            "real_gold_qualified": False,
            "paid_model_calls": 0,
            "canonical_world_writes": 0,
        }


if __name__ == "__main__":
    print(json.dumps(run_browser_e2e(), ensure_ascii=False, indent=2))
