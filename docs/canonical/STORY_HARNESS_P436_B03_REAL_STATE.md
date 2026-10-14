# P4.36 — B03 genuine English Master → Q25 → read-only Final StoryState

Status: **actual original evidence proven**, 2026-10-14; PR #275 remains Draft; no production/main/Canon writes.

## Source-sealed independent sequence

| Stage | Original immutable proof |
|---|---|
| B03 10-year-old real SpineForge → Writer | [#38509072620](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38509072620), 1,300 EN words, 6 beats, $0.067720 |
| Independent source-sealed Sonnet initial QA | [#38517447515](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38517447515), ACCEPT, reader 4/5, zero blockers, $0.027522 |
| Immutable pilot-only English Master | [#38524014932](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38524014932), exact original Writer bytes, 0 model calls |
| Genuine Sonnet Q25 | [#38526833719](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38526833719), $0.031366, generation `gen-1791962013-EUhZDIwF6TSPzFoV4B9S` |
| Real Q25 deterministic final-state projection | [#38528271947](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38528271947), 0 model calls, read-only |

Frozen source pack: `b55ba5c57a3abda0a1b4ef18fe98284f4fea7511b1b82281585ac9da77a205c0`.
Original Spine: `9a0b0476c2c5f94bc5e7f3a6d0261cefbee9ce22062c02f8a55fed761c10a9ad`.
Original Writer/master: `80fa8224c78c494b13bc347ecabdfff75fd5c9e1638ad88ee9ba47c6986643f9`.
Original Master manifest receipt SHA: `b79feaff670c21a0b334c540ab1c51dda437866d412fba8c20e54eee0f863c0b`.
Original Q25 evidence receipt SHA: `dc6145aba4c714fb2d706dfd0639f524571fede4b58409be0d181f432641322c`.
Read-only state receipt SHA: `32deb6cd448d8d8f301298436ee22fd115e545c554aabce893f853caad56b55a`.

Immutable repository evidence:
- `evidence/story_harness_p431/` (four original provider generation records)
- `evidence/story_harness_p433/b03-r06-original-independent-quality-accept.json`
- `evidence/story_harness_p434/b03-r06-pilot-master-manifest.json`
- `evidence/story_harness_p435/b03-r06-original-q25-evidence.json`
- `evidence/story_harness_p436/b03-r06-real-read-only-final-state-draft.json`

## State evidence (never Canon)

- Duru starts at **RIVERBANK**. Evidence quotes support the new discovery **VILLAGE** and a proposed final location in **VILLAGE**.
- **Three observed objects**: key `AT_VILLAGE`, chest `AT_VILLAGE`, sweet bread `HELD_BY_PROTAGONIST`. All ownership remains **UNKNOWN**, even where the story narrates possession.
- The rule **“Nehir yalnızca tek geçişte aşılır” remains OPEN**. The requirement that the chest cannot open before its lock is opened is observed as **SATISFIED**.
- Original canonical obligations remain present, without final semantic certification.
- Unobserved owners/locations remain explicitly unknown. The elapsed world-time delta is unobserved, and final world time stays `null`.
- `canon_commit_authorized=false`, `production_change=false`, `independent_final_state_semantic_certification=false`, `original_full_frozen_v21_4_final_quality_verified=false`.

The original Q25 and state evidence was taken from successful protected GitHub runner artifacts; the full read-only replay compares the original protected claims **byte-for-byte** to these frozen repository files. Later PR checks only re-read the existing state; **they never attempt a second freeze or provider POST**.

## Cost ledger

The three known B03 stage charges were **$0.067720 + $0.027522 + $0.031366 = $0.126608**, reported by the provider. Prior B01/B02 known charges are **$0.251838**; combined known paid-model receipt total for these documented calls is **$0.378446**. A separate **$1.130000** unknown-charge safety hold is retained. Including unspent reserved stages **$0.031112**, conservative reserved exposure is **$1.539558** of the authorized $10.00. This is a working cap/ledger, not an invoice reconciliation.

## What is not being claimed

No original frozen v21.4 final audit, no human reading validation, no released world state and no proven 90% reliability. B01/B02/B03 complete *initial pilot* chains but not production release qualification. The next controlled candidate is **B04**; the budgeted 10×3 pilot planning and explicit holdout measurement rules belong to P4.37.
