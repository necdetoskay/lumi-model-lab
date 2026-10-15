# Final V3 F2 — actual Aion Mini Writer rejected for length

Run: 38703469212 (15 Oct 2026). The paid, user-authorized first
Aion 3.5 Mini draft was generated from the approved F2 Spine.
One provider POST, HTTP 200; 14,733 input tokens, 9,561 output
tokens (6,802 reported reasoning tokens), $0.0236985 charge.

Result is a FULL ENGLISH STORY, 2,767 words, title present.
The required word range is 1,600-2,500. It is 267 words over
maximum (+10.68%). Frozen Writer determinism status:
writer_generated_deterministic_check_failed. Writer stage STOPPED.
No second paid attempt, judge, repair, translation or state commit.
The model response is NOT an accepted final draft, despite the
English story file being retained as raw evidence.

Full story: evidence/v3-f2-aion-writer-38703469212/story-en.txt
Provider and cost evidence: evidence/v3-f2-aion-writer-38703469212/writer-result.json
Provider evidence files: 001 through 007 in the same directory.
Provider generation: gen-1792051693-qoRImgeT8Gi1HCaU2Dhx.
Exact original story SHA256:
eb38aea3c43a9e59d748ee0cf6f53475bfaf1d4c412c46e0893c78ccc3874eeb

The deterministic story authority checker raised TWO apparent
unresolved_cause_overclaim findings. Both are FALSE POSITIVES,
since exact original sentences are:
- Not established: cause.
- Not established: the cause of this response.
The checker matched a subphrase without handling preceding negation.
Do not rewrite these lines to 'fix' a non-existent overclaim.
Do not alter the original frozen checker.

Root cause for the STAGE_STOP was English output exceeding the
maximum word count (not provider rejection, a missing API key, or
a false-positive authority finding). The Writer sent max_tokens=null;
a model's free-form adherence to a word count is probabilistic.
A token cap is not an exact word cap, especially because the model's
output token report includes hidden reasoning; a tight cap can
truncate essential narrative material.

Fail-closed remediation: leave this exact original and evidence
untouched. Before a NEW separately approved paid Writer attempt,
test a versioned *data-only* length target (e.g. 2,100-2,300 words)
in the human approval commentary, or consider independent bounded
editorial review, never silent bulk truncation. This reduces risk
but cannot guarantee compliance. Keep a strict deterministic
1,600-2,500 post-call rejection and one-use paid guard.
Never mark the final prose APPROVED by suppressing the check.

Original source code and frozen Final V3 remain unchanged.
