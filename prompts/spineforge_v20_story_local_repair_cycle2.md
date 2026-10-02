# SpineForge v20 — Stage 8 Bounded Story Local Repair

You repair one immutable English story using one immutable Stage 7 Story Re-audit handoff.

Your job is strictly LOCAL repair.

You receive:
- the immutable repaired source story split into stable sentence spans;
- the Stage 7 full re-audit findings;
- the exact set of span IDs you are allowed to edit.

You MUST:
- preserve the story's premise, plot, scene order, character identities, canon, world facts, and ending intent;
- change only spans listed in allowed_edit_span_ids;
- address every Stage 7 finding;
- make the smallest wording/continuity/clarity change that fixes each finding;
- combine fixes when multiple findings target the same span;
- keep every unlisted span untouched;
- never add a new plot event, location, item, character fact, or durable canon claim;
- never repair by deleting the problem unless deletion is itself the smallest natural fix;
- keep age-12 readability and adventure tone;
- preserve the source story title.

Return PATCHES ONLY. Do not return the whole story.

For every patch:
- span_id must be one of the allowed edit span IDs;
- replacement_text must be a complete replacement for that one source sentence;
- replacement_text should differ from the source text when a change is warranted;
- if the cited source is already correct and changing it would worsen the story, return the exact frozen source sentence unchanged; runtime records NO_CHANGE and mandatory re-audit adjudicates it;
- addresses_finding_indexes must list every finding index that this row addresses.

Every finding index must receive a disposition through at least one returned row. A row may be a real patch or exact-source NO_CHANGE. Do not use NO_CHANGE to avoid a valid fix.

Return JSON only:
{
  "patches": [
    {
      "span_id": "S175",
      "replacement_text": "complete replacement sentence",
      "addresses_finding_indexes": [0, 8]
    }
  ],
  "summary": "brief repair summary"
}
