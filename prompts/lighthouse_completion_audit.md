Audit the entire current English story against approved_plan after bounded patch repair.
Check the previous defect, all effects of edits, and publication-blocking regressions.
Also independently check the whole plot: character/creature scale and limits; exact entry,
exit and rescue geography; scene end states; responsibility and irreversible compass loss;
absence of new tools, powers, rescue routes or rewards; and the specified closing image.
Do not overlook changed geography merely because the broad story events are similar.
Do not accept automatically because a patch claims outside_patches_unchanged.
Do not invent a contradiction: distinguish explicitly constrained dimensions from those
left unspecified. A failed attempt is not evidence that the attempted action succeeded.
Ignore the historical upper word limit; target_words is minimum-only.
Report material, grounded defects, not optional prose polish. Use canon_integrity or
spine_fidelity for material plan violations. Minor style or pacing is advisory.
If necessary changes span multiple scenes, identify all relevant sentence IDs together;
select every span needing modification, up to 24 per finding. Avoid requesting a full rewrite
when precise changes can resolve the issue. Use SCENE_REPAIR for bounded changes, even
across scenes; STRUCTURAL_REPAIR or REPLAN only when required by the actual defect.
For every finding return family, severity, repair_scope, span_ids, exact_text, reason.
Return JSON only. Empty findings means no material defect found in this pass, not a guarantee.
Wire prose is a table: concatenate whitespace_before + current_text, then trailing_whitespace.

Compare each required_end_state with the actual story, including the final paragraph.
An image appearing earlier is not sufficient if a different ending follows it. Additional
entry/exit routes or substituted endings materially changing the approved plan are
spine_fidelity findings of at least moderate severity, even if physically plausible.
Do not confuse a plan deviation with optional stylistic preference.
