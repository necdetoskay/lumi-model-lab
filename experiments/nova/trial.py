"""Export and import boundary for future independent human/manual story trials.

This module never invokes a generator or purchases inference. Imported metadata
are operator attestations, not authenticated provider billing or human identity.
"""
from pathlib import Path

from experiments.narrative_mechanics import core as nml
from . import evaluate as ev, vault


def prepare_trial(directory, seed=314159, repeats=3):
    directory = Path(directory)
    if directory.exists():
        raise nml.Invalid("OUTPUT_EXISTS_USE_NEW_DIRECTORY")
    rows, state, briefs, release = ev.load_inputs()
    requests, allocation = ev.prepare(rows, state, briefs, seed, repeats)
    ev.write_new(directory / "private/requests.json", requests)
    ev.write_new(directory / "private/allocation.json", allocation)
    manifest = {"schema": "nova.trial.v1", "mode": "EXTERNAL_STORIES_PENDING",
                "seed": seed, "repeats": repeats, "release_sha256": nml.fingerprint(release),
                "requests_sha256": nml.fingerprint(requests), "allocation_sha256": nml.fingerprint(allocation),
                "paid_dispatch_authorized": False, "integration_authorized": False}
    ev.write_new(directory / "manifest.json", manifest)
    return manifest


def load_trial(directory):
    directory = Path(directory)
    manifest = nml.read_json(directory / "manifest.json")
    rows, state, briefs, release = ev.load_inputs()
    requests, allocation = ev.prepare(rows, state, briefs, manifest["seed"], manifest["repeats"])
    # Reconstruct from pinned release: jointly changing manifest and allocation cannot self-certify.
    if (manifest.get("mode") != "EXTERNAL_STORIES_PENDING" or manifest.get("paid_dispatch_authorized") is not False
            or manifest.get("integration_authorized") is not False
            or manifest["release_sha256"] != nml.fingerprint(release)
            or nml.read_json(directory / "private/requests.json") != requests
            or nml.read_json(directory / "private/allocation.json") != allocation
            or manifest["requests_sha256"] != nml.fingerprint(requests)
            or manifest["allocation_sha256"] != nml.fingerprint(allocation)):
        raise nml.Invalid("TRIAL_BINDING")
    return requests, allocation, state


def import_stories(directory, bundle):
    requests, allocation, state = load_trial(directory)
    if set(bundle) != {"schema", "mode", "generator", "authorization_reference", "approved_budget_microusd",
                       "actual_cost_microusd", "stories"} or bundle["schema"] != "nova.story-bundle.v1":
        raise nml.Invalid("STORY_BUNDLE_SCHEMA")
    if bundle["mode"] not in ("HUMAN_MANUAL", "EXTERNAL_AUTHORIZED_MODEL"):
        raise nml.Invalid("FIXTURES_NOT_REAL_STORIES")
    for field in ("approved_budget_microusd", "actual_cost_microusd"):
        if type(bundle[field]) is not int or bundle[field] < 0:
            raise nml.Invalid("COST_ACCOUNTING")
    if bundle["actual_cost_microusd"] > bundle["approved_budget_microusd"]:
        raise nml.Invalid("BUDGET_EXCEEDED")
    if not isinstance(bundle["generator"], str) or not bundle["generator"].strip():
        raise nml.Invalid("GENERATOR_PROVENANCE")
    if bundle["mode"] == "EXTERNAL_AUTHORIZED_MODEL" and not bundle["authorization_reference"]:
        raise nml.Invalid("EXTERNAL_AUTHORIZATION_MISSING")
    if bundle["mode"] == "HUMAN_MANUAL" and (bundle["actual_cost_microusd"] or bundle["approved_budget_microusd"]):
        raise nml.Invalid("MANUAL_MODE_HAS_MODEL_COST")
    if not isinstance(bundle["stories"], list):
        raise nml.Invalid("STORY_BUNDLE_SCHEMA")
    for story in bundle["stories"]:
        if set(story) != {"sample_id", "text"} or not all(isinstance(v, str) for v in story.values()):
            raise nml.Invalid("STORY_SCHEMA")
    packet = ev.blind_packet(bundle["stories"], allocation)
    limits = {r["sample_id"]: r["common"]["max_words"] for r in requests}
    archive = [p.read_text(encoding="utf-8") for a in nml.ARCHIVES for p in (nml.ROOT / a).rglob("S*.md")]
    for sample in packet:
        if not 30 <= len(vault.tokens(sample["text"])) <= limits[sample["sample_id"]]:
            raise nml.Invalid("STORY_LENGTH_GATE")
        if ev.lexical_gates(sample["text"], state, archive):
            raise nml.Invalid("STORY_LEXICAL_GATE")
    destination = Path(directory) / "review"
    if destination.exists():
        raise nml.Invalid("REVIEW_PACKET_EXISTS")
    # Only review/* is given to raters. They receive the same frozen state and briefs.
    ev.write_new(destination / "blind-packet.json", packet)
    context = {"state": state, "briefs": [r["common"]["brief"] for r in requests]}
    context["briefs"] = list({b["id"]: b for b in context["briefs"]}.values())
    ev.write_new(destination / "context.json", context)
    ev.write_new(Path(directory) / "private/imported-bundle.json", bundle)
    ev.write_new(Path(directory) / "private/import-receipt.json",
                 {"bundle_sha256": nml.fingerprint(bundle), "packet_sha256": nml.fingerprint(packet)})
    return {"status": "IMPORTED_FOR_BLIND_REVIEW", "stories": len(packet), "semantic_gates": "HUMAN_REVIEW_REQUIRED",
            "provider_calls_by_nova": 0, "external_cost_microusd_attested": bundle["actual_cost_microusd"]}


def score_trial(directory, ballots):
    _, allocation, _ = load_trial(directory)
    directory = Path(directory)
    bundle = nml.read_json(directory / "private/imported-bundle.json")
    packet = nml.read_json(directory / "review/blind-packet.json")
    receipt = nml.read_json(directory / "private/import-receipt.json")
    if receipt != {"bundle_sha256": nml.fingerprint(bundle), "packet_sha256": nml.fingerprint(packet)}:
        raise nml.Invalid("IMPORT_RECEIPT_CHANGED")
    if packet != ev.blind_packet(bundle["stories"], allocation):
        raise nml.Invalid("IMPORTED_STORY_CHANGED")
    if any(b.get("reviewer") == bundle["generator"] for b in ballots):
        raise nml.Invalid("GENERATOR_CANNOT_SCORE")
    report = ev.score(packet, allocation, ballots, fixture=False)
    report.update({"provider_calls_by_nova": 0, "actual_cost_microusd_attested": bundle["actual_cost_microusd"],
                   "ballots_sha256": nml.fingerprint(ballots), "packet_sha256": nml.fingerprint(packet),
                   "allocation_sha256": nml.fingerprint(allocation),
                   "authenticity": "OPERATOR_ATTESTED_NOT_CRYPTOGRAPHICALLY_VERIFIED",
                   "source_review": "PENDING", "overall_maturity": "NOT_ESTABLISHED"})
    nml.freeze(directory / "private/ballots", "ballots", ballots)
    path = nml.freeze(directory / "reports", "evaluation", report)
    return {"report": str(path), **report}
