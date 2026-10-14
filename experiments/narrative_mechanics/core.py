"""LAB ONLY. Standard library, no model/provider/database/pipeline imports.

Raw archive -> private evidence -> pinned abstract vocabulary -> writer preview.
The public boundary accepts a selection request, never arbitrary writer prose.
"""
from __future__ import annotations

import copy
import hashlib
import itertools
import json
from pathlib import Path, PurePosixPath
import re
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ARCHIVE_COMMIT = "9ae2874cabe582f9e626fc77f36cd208ad234600"
ARCHIVES = ("docs/research/stargate-sg1", "docs/research/stargate-atlantis")
COUNTS = {"sg1": [22] * 7 + [20] * 3, "atlantis": [20] * 5}
AXES = ("event", "rule", "curiosity", "conflict", "decision", "cost", "reveal", "persistent_state")
# Release changes require code review, a new content-addressed file and new tests.
RELEASE_SHA256 = "13ea240897d88ba2bc4264fd75e514639402462b43a42ff697b4da4f0546940a"


class Invalid(ValueError):
    """Fail-closed research contract violation; never contains source text."""


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def fingerprint(value):
    return sha(canonical(value))


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise Invalid("DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def read_json(path):
    try:
        return json.loads(Path(path).read_bytes(), object_pairs_hook=_pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(Invalid("NONFINITE_JSON")))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise Invalid("INVALID_JSON") from exc


def validate(value, schema, location="$", root=None):
    """Small closed JSON Schema subset used by our checked-in schemas only.

    Supported keywords are deliberately explicit; unknown keywords fail closed.
    Published schemas are also usable by a full Draft 2020-12 validator.
    """
    root = schema if root is None else root
    supported = {"$schema", "$id", "$defs", "$ref", "title", "description", "type", "properties",
                 "required", "additionalProperties", "items", "minItems", "maxItems", "uniqueItems",
                 "minimum", "maximum", "minLength", "maxLength", "pattern", "enum", "const"}
    if set(schema) - supported:
        raise Invalid("UNSUPPORTED_SCHEMA_KEYWORD")
    if "$ref" in schema:
        ref = schema["$ref"]
        if not ref.startswith("#/$defs/") or ref.count("/") != 2:
            raise Invalid("EXTERNAL_SCHEMA_REF")
        return validate(value, root["$defs"][ref.rsplit("/", 1)[1]], location, root)
    types = {"object": dict, "array": list, "string": str, "integer": int, "boolean": bool, "null": type(None)}
    if "type" in schema and type(value) is not types[schema["type"]]:
        raise Invalid("SCHEMA_TYPE:" + location)
    if "const" in schema and (type(value) is not type(schema["const"]) or value != schema["const"]):
        raise Invalid("SCHEMA_CONST:" + location)
    if "enum" in schema and not any(type(value) is type(x) and value == x for x in schema["enum"]):
        raise Invalid("SCHEMA_ENUM:" + location)
    if isinstance(value, dict):
        properties = schema.get("properties", {})
        if set(schema.get("required", [])) - value.keys():
            raise Invalid("SCHEMA_MISSING:" + location)
        if schema.get("additionalProperties") is False and value.keys() - properties.keys():
            raise Invalid("SCHEMA_EXTRA:" + location)
        for key, sub in properties.items():
            if key in value:
                validate(value[key], sub, location + "." + key, root)
    if isinstance(value, list):
        if not schema.get("minItems", 0) <= len(value) <= schema.get("maxItems", float("inf")):
            raise Invalid("SCHEMA_ARRAY_SIZE:" + location)
        if schema.get("uniqueItems") and len({canonical(x) for x in value}) != len(value):
            raise Invalid("SCHEMA_DUPLICATE:" + location)
        for index, item in enumerate(value):
            validate(item, schema.get("items", {}), location + "[" + str(index) + "]", root)
    if isinstance(value, str):
        if not schema.get("minLength", 0) <= len(value) <= schema.get("maxLength", float("inf")):
            raise Invalid("SCHEMA_STRING_SIZE:" + location)
        if "pattern" in schema and re.search(schema["pattern"], value) is None:
            raise Invalid("SCHEMA_PATTERN:" + location)
    if type(value) is int and not schema.get("minimum", -float("inf")) <= value <= schema.get("maximum", float("inf")):
        raise Invalid("SCHEMA_RANGE:" + location)


def schema(name):
    return read_json(HERE / "schemas" / (name + ".schema.json"))


def safe_path(root, relative):
    path = PurePosixPath(relative)
    if path.is_absolute() or ".." in path.parts or "\\" in relative or ":" in relative or str(path) != relative:
        raise Invalid("UNSAFE_PATH")
    base = Path(root).resolve()
    result = base.joinpath(*path.parts)
    for part in (result, *result.parents):
        if part == base:
            break
        if part.is_symlink():
            raise Invalid("SYMLINK_FORBIDDEN")
    if not result.resolve().is_relative_to(base):
        raise Invalid("PATH_ESCAPE")
    return result


def freeze(directory, prefix, value):
    """Content-addressed, exclusive creation; identical repeat is idempotent."""
    if re.fullmatch(r"[a-z][a-z0-9-]*", prefix) is None:
        raise Invalid("UNSAFE_ARTIFACT_PREFIX")
    data = canonical(value) + b"\n"
    path = Path(directory) / (prefix + "-" + sha(data) + ".json")
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as stream:
            stream.write(data)
    except FileExistsError:
        if path.is_symlink() or path.read_bytes() != data:
            raise Invalid("IMMUTABLE_COLLISION")
    return path


def _git(root, *args):
    try:
        return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True).stdout
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        raise Invalid("FROZEN_GIT_OBJECT_UNAVAILABLE") from exc


def build_manifest(root=ROOT):
    """Hash immutable Git blob bytes, never platform-dependent text reads."""
    tree = _git(root, "ls-tree", "-rz", ARCHIVE_COMMIT, "--", *ARCHIVES)
    files, episodes, entries = [], [], []
    for row in tree.split(b"\0"):
        if not row:
            continue
        meta, path_bytes = row.split(b"\t", 1)
        mode, kind, oid = meta.decode().split()
        if mode != "100644" or kind != "blob":
            raise Invalid("NONREGULAR_ARCHIVE_ENTRY")
        path = path_bytes.decode("utf-8")
        entries.append((path, oid))
    try:
        batch = subprocess.run(["git", "-C", str(root), "cat-file", "--batch"],
                               input=("\n".join(oid for _, oid in entries) + "\n").encode(),
                               capture_output=True, check=True).stdout
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        raise Invalid("FROZEN_GIT_OBJECT_UNAVAILABLE") from exc
    offset = 0
    for path, oid in entries:
        boundary = batch.index(b"\n", offset)
        header = batch[offset:boundary].decode().split()
        if len(header) != 3 or header[:2] != [oid, "blob"]:
            raise Invalid("FROZEN_BLOB_UNAVAILABLE")
        size = int(header[2])
        data = batch[boundary + 1:boundary + 1 + size]
        offset = boundary + size + 2
        files.append({"path": path, "git_blob": oid, "sha256": sha(data), "bytes": len(data)})
        match = re.fullmatch(r"docs/research/stargate-(sg1|atlantis)/season-(\d{2})/(S(\d{2})E(\d{2}))-[a-z0-9-]+\.md", path)
        if match:
            series, folder, code, season, episode = match.groups()
            if folder != season:
                raise Invalid("EPISODE_DIRECTORY_MISMATCH")
            text = data.decode("utf-8")
            for field, expected in (("season", str(int(season))), ("episode", str(int(episode))), ("status", "complete")):
                if not re.search(r"^" + field + ": " + expected + r"$", text, re.M):
                    raise Invalid("EPISODE_METADATA_MISMATCH")
            episodes.append({"id": series + ":" + code, "path": path, "sha256": sha(data)})
    expected = {f"{series}:S{s:02}E{e:02}" for series, counts in COUNTS.items()
                for s, count in enumerate(counts, 1) for e in range(1, count + 1)}
    if {x["id"] for x in episodes} != expected or len(episodes) != 314:
        raise Invalid("ARCHIVE_EPISODE_COVERAGE")
    return {"schema": "nml.archive.v1", "scope": "LAB_ONLY", "source_commit": ARCHIVE_COMMIT,
            "source_kind": "SECONDARY_TURKISH_SUMMARIES", "semantic_accuracy": "NOT_REVERIFIED",
            "files": sorted(files, key=lambda x: x["path"]), "episodes": sorted(episodes, key=lambda x: x["id"])}


def verify_archive(manifest, root=ROOT):
    # Rebuild from the pinned Git commit: altered manifest + altered source cannot self-certify.
    if manifest != build_manifest(root):
        raise Invalid("ARCHIVE_MANIFEST_MISMATCH")
    actual = set()
    for archive in ARCHIVES:
        folder = safe_path(root, archive)
        for path in folder.rglob("*"):
            relative = path.relative_to(root).as_posix()
            safe_path(root, relative)
            if path.is_file():
                actual.add(relative)
    if actual != {x["path"] for x in manifest["files"]}:
        raise Invalid("ARCHIVE_MEMBERSHIP_CHANGED")
    for entry in manifest["files"]:
        data = safe_path(root, entry["path"]).read_bytes()
        if len(data) != entry["bytes"] or sha(data) != entry["sha256"]:
            raise Invalid("ARCHIVE_BYTES_CHANGED")


def validate_extraction(record, manifest, root=ROOT):
    validate(record, schema("extraction"))
    if record["archive_sha256"] != fingerprint(manifest):
        raise Invalid("EXTRACTION_ARCHIVE_MISMATCH")
    sources = {x["id"]: x for x in manifest["episodes"]}
    if record["source_id"] not in sources:
        raise Invalid("UNKNOWN_EPISODE")
    source = sources[record["source_id"]]
    data = safe_path(root, source["path"]).read_bytes()
    if sha(data) != source["sha256"]:
        raise Invalid("EXTRACTION_SOURCE_CHANGED")
    for axis in AXES:
        claim = record["axes"][axis]
        unknown = claim["epistemic"] in ("UNKNOWN", "NOT_APPLICABLE")
        if unknown and (claim["spans"] or claim["score"] != 0):
            raise Invalid("UNKNOWN_HAS_EVIDENCE_OR_SCORE")
        if not unknown and (not claim["spans"] or claim["score"] == 0):
            raise Invalid("CLAIM_REQUIRES_EVIDENCE")
        for span in claim["spans"]:
            start, end = span["start_byte"], span["end_byte"]
            if not 0 <= start < end <= len(data):
                raise Invalid("SPAN_RANGE")
            piece = data[start:end]
            try:
                piece.decode("utf-8")
                data[:start].decode("utf-8")
            except UnicodeError as exc:
                raise Invalid("SPAN_UTF8_BOUNDARY") from exc
            if sha(piece) != span["sha256"]:
                raise Invalid("SPAN_HASH")
    # Byte integrity is NOT semantic support, human approval or accepted state.


def load_release(root=ROOT):
    release_path = HERE / "releases" / ("release-" + RELEASE_SHA256 + ".json")
    if release_path.is_symlink() or sha(release_path.read_bytes()) != RELEASE_SHA256:
        raise Invalid("RELEASE_CHANGED")
    release = read_json(release_path)
    artifacts = {}
    for name, entry in release["artifacts"].items():
        path = safe_path(HERE, entry["path"])
        if sha(path.read_bytes()) != entry["sha256"]:
            raise Invalid("RELEASE_ARTIFACT_CHANGED")
        artifacts[name] = read_json(path)
    # Schemas are pinned too. Never use a mutable schema as the integrity boundary.
    for name, entry in release["schemas"].items():
        if sha(safe_path(HERE, entry["path"]).read_bytes()) != entry["sha256"]:
            raise Invalid("RELEASE_SCHEMA_CHANGED")
    manifest = artifacts["archive"]
    verify_archive(manifest, root)
    cards, templates = artifacts["cards"], artifacts["templates"]
    validate(cards, schema("cards"))
    validate(templates, schema("templates"))
    ids = [c["id"] for c in cards]
    if len(set(ids)) != len(ids) or set(ids) != {t["id"] for t in templates} or len(templates) != len(ids):
        raise Invalid("CARD_TEMPLATE_IDENTITIES")
    sources = {x["id"] for x in manifest["episodes"]}
    records = artifacts["extractions"]
    for record in records:
        validate_extraction(record, manifest, root)
    evidence = {r["id"]: r for r in records}
    if len(evidence) != len(records):
        raise Invalid("DUPLICATE_EXTRACTION")
    for card in cards:
        if not set(card["source_ids"]) <= sources:
            raise Invalid("CARD_SOURCE_REFERENCE")
        if card["extraction_id"] not in evidence or evidence[card["extraction_id"]]["source_id"] not in card["source_ids"]:
            raise Invalid("CARD_EXTRACTION_REFERENCE")
        if card["age_min"] > card["age_max"]:
            raise Invalid("CARD_AGE_RANGE")
        if card["source_group"] != card["source_ids"][0].split(":")[0]:
            raise Invalid("CARD_SOURCE_GROUP")
    return artifacts


def _eligible(card, request):
    reasons = []
    if card["status"] != "PROPOSED_LAB":
        reasons.append("CARD_WITHHELD")
    if not card["age_min"] <= request["age"] <= card["age_max"]:
        reasons.append("AGE")
    if card["family"] not in request["families"]:
        reasons.append("FAMILY")
    if set(card["risks"]) & set(request["forbidden_risks"]):
        reasons.append("SAFETY")
    # Non-overridable floor for younger readers, even if caller omits restrictions.
    if request["age"] < 10 and set(card["risks"]) & {"loss", "identity_uncertainty", "ethical_conflict"}:
        reasons.append("AGE_SAFETY_FLOOR")
    if not set(card["requires"]) <= set(request["authorized_features"]):
        reasons.append("CANON_REQUIREMENTS")
    if not set(card["effects"]) <= set(request["allowed_effects"]):
        reasons.append("STATE_PERMISSION")
    if card["reveal_level"] > request["reveal_ceiling"]:
        reasons.append("REVEAL_CEILING")
    if card["id"] in request["recent_ids"]:
        reasons.append("RECENT_REPEAT")
    return reasons


def select(request, *, root=ROOT):
    """Return two distinct views; CLI exports only writer unless audit requested.

    Deterministic exact search on the bounded v1 catalog (<=20 cards), no RNG.
    No best-effort unsafe fallback: an unsatisfied request returns zero cards.
    """
    artifacts = load_release(root)
    validate(request, schema("request"))
    cards = artifacts["cards"]
    ids = {x["id"] for x in cards}
    if not set(request["recent_ids"]) <= ids:
        raise Invalid("UNKNOWN_RECENT_CARD")
    rejected = {c["id"]: _eligible(c, request) for c in cards}
    eligible = sorted((c for c in cards if not rejected[c["id"]]), key=lambda c: c["id"])
    choices = []
    for combo in itertools.combinations(eligible, request["count"]):
        families = [c["family"] for c in combo]
        groups = [c["source_group"] for c in combo]
        if len(set(families)) < request["min_families"]:
            continue
        if len(set(groups)) < request["min_source_groups"]:
            continue
        if any(families.count(x) > request["max_per_family"] for x in set(families)):
            continue
        if any(groups.count(x) > request["max_per_source_group"] for x in set(groups)):
            continue
        # Prefer diversity, then request-bound SHA tie break; order independent.
        selected_ids = [c["id"] for c in combo]
        rank = (-len(set(families)), -len(set(groups)), fingerprint({"seed": request["seed"], "ids": selected_ids}))
        choices.append((rank, combo))
    chosen = min(choices, key=lambda x: x[0])[1] if choices else ()
    template_map = {x["id"]: x for x in artifacts["templates"]}
    writer = {"schema": "nml.writer-preview.v1", "scope": "LAB_ONLY", "status": "PROPOSED" if chosen else "ABSTAIN",
              "state_commit_authorized": False, "semantic_support_certified": False,
              "mechanics": [copy.deepcopy(template_map[c["id"]]) for c in chosen]}
    validate(writer, schema("writer"))
    audit = {"schema": "nml.selection-audit.v1", "scope": "LAB_ONLY", "release_sha256": RELEASE_SHA256,
             "request_sha256": fingerprint(request), "canon_fingerprint": request["canon_fingerprint"],
             "selected_ids": [c["id"] for c in chosen], "exclusions": {k: v for k, v in sorted(rejected.items()) if v},
             "eligible_ids": [c["id"] for c in eligible], "reason": "SELECTED" if chosen else "NO_FEASIBLE_SET",
             "writer_sha256": fingerprint(writer), "provider_calls": 0, "paid_ai_usd": 0}
    return writer, audit
