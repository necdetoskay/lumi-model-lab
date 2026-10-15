# Final V3 new revision — No client output token ceilings (2026-10-15)

## Triggering real failure
- Paid run: [38780429688](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38780429688)
- Case: `age18.closed-platform.mystery.stress-01` (Mara).
- Model: `anthropic/claude-sonnet-5.5`.
- HTTP 200, `finish_reason=length`, `native_finish_reason=max_tokens`.
- Input: 10,998 tokens. Completion: **12,000/12,000** tokens, of which **3,674** reasoning.
- Provider-confirmed cost: **$0.141996**.
- Partial JSON: `STRUCTURED_JSON_RESPONSE_TRUNCATED`. No Luna gate, no Writer, no translation; downstream 3 cases not run.
- Automatic retry count: zero. Former once-only user-granted paid claim is spent and **must not be reused**.

## Correction
Create a distinct, versioned `AGE18-V3-UNCAPPED-v1` runtime (not a silent mutation of the original frozen v2 reference). Remove all nine fixed `max_tokens=N` call-site values in the complete Final V3 active stages:

1. `src/episode_spine_v2_generate.py`: Sonnet 5.5 Spine Architect **12,000 -> omit**, Luna Spine Gate **6,000 -> omit**.
2. `src/episode_authority_gate_v1.py`: Luna English authority gate **1,800 -> omit**.
3. `src/episode_authority_adjudication_v1.py`: adjudication **1,800 -> omit**.
4. `src/episode_bounded_repair_v1.py`: Sol English model repair **2,400 -> omit**.
5. `src/episode_translation_v1.py`: Gemini Turkish translation **8,000 -> omit**.
6. `src/episode_translation_repair_v1.py`: Gemini translation repair **2,000 -> omit**.
7. `src/episode_fidelity_v1.py`: Luna Turkish fidelity **2,200 -> omit**.
8. `src/episode_fidelity_adjudication_v1.py`: Sol fidelity adjudication **1,800 -> omit**.

Aion Writer already uses `max_tokens=None`, unchanged. `src/generate.py` omits the `max_tokens` request key when the caller passes `None`. Profile normalization was checked for all exact active role+request-class combinations. No `max_tokens` or `max_completion_tokens` is emitted on the actual constructed HTTP payload under mocked transport.

The external single-use paid Spine guard now explicitly **rejects any outgoing output-token ceiling before provider POST** (also checks `max_output_tokens`). It does not increase retries or budgets.

## New freeze and case input routing
- New profile: `data/specifications/story_lab/age18_story_lane_profile_v3_uncapped.json`
- New lane revision: `AGE18-V3-UNCAPPED-v1`
- Source: the 43-file SHA-256 manifest rederived for this new branch; old v2 reference remains in version history.
- Four case manifests point to **new** revision; all remain `paid_spine_authorized=false`, `human_spine_approval=false`.
- The historical v2 frozen profile cannot verify this modified runtime and should **not** be used to run a paid stage against it. Do not change history to make the legacy verifier pass.

## Verification
- Connected CI runner clean temporary checkout: **25/25 new tests PASS**.
- New `verify_frozen_lane`: **43/43 PASS**.
- Four independent `CharacterSagaSpineV2` inputs and controlled-premise schemas validate.
- No new paid model calls; no new spending; no story text edits, Canon state commits or publication.
- Provider/upstream model capacity remains finite and outside LUMI control. "Uncapped" means LUMI does not put an explicit output-token ceiling in the request; it does not assert infinite provider output.
- An explicit fresh one-use paid grant is mandatory for any future trial; old claim cannot be used.
