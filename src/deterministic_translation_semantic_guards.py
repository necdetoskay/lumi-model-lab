from __future__ import annotations

import re
from typing import Any


def _first_heading(text: str) -> str:
    for line in text.splitlines():
        line=line.strip()
        if line.startswith("#"):
            return line.lstrip("#").strip()
    return ""


def _source_title_has_uncertainty(title: str) -> bool:
    return bool(re.search(r"\b(?:might|may|could|possibly|perhaps)\b", title, re.IGNORECASE))


def _target_title_has_uncertainty(title: str) -> bool:
    patterns=[
        r"\bgerekebilir\b",
        r"\bgerekebilecek\b",
        r"\bolabilir\b",
        r"\bolabilecek\b",
        r"\bbelki\b",
        r"\bmuhtemel(?:en)?\b",
        r"\bihtimal(?:i|en)?\b",
    ]
    return any(re.search(p,title,re.IGNORECASE) for p in patterns)


def _source_has_recurrence_repeatability_distinction(source: str) -> bool:
    has_recurrence=bool(re.search(r"\brecurr(?:ence|ing|ent)?\b",source,re.IGNORECASE))
    has_repeatability=bool(
        re.search(r"\brepeatab(?:le|ility)\b|\breproduc(?:e|ed|ible|ibility)\b",source,re.IGNORECASE)
    )
    return has_recurrence and has_repeatability


def run_translation_semantic_guards(
    source_en: str,
    translation_tr: str,
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]]=[]

    src_title=_first_heading(source_en)
    tr_title=_first_heading(translation_tr)
    if _source_title_has_uncertainty(src_title) and not _target_title_has_uncertainty(tr_title):
        findings.append({
            "guard_id":"title_modality_preservation",
            "severity":"serious",
            "family":"translation_fidelity",
            "source_quote":src_title,
            "translation_quote":tr_title,
            "reason":"Source title contains explicit uncertainty/modality but Turkish title states the proposition without an uncertainty marker.",
        })

    if _source_has_recurrence_repeatability_distinction(source_en):
        collapsed=[]
        for line in translation_tr.splitlines():
            lower=line.lower()
            # In this lane, 'tekrarlanabilirlik' is reserved for independent
            # repeatability. It must not be used to translate recurrence state.
            if "tekrarlanabilirlik bilinmiyor" in lower:
                collapsed.append(line.strip())
            if re.search(r"neden[,;]?\s*tekrarlanabilirlik\s+veya\s+seyir\s+riski", lower):
                collapsed.append(line.strip())
            if re.search(r"neden[,;]?\s*tekrarlanabilirlik\s+veya\s+.*risk", lower):
                collapsed.append(line.strip())

        if collapsed:
            findings.append({
                "guard_id":"recurrence_repeatability_distinction",
                "severity":"serious",
                "family":"translation_fidelity",
                "source_quote":"recurrence / independent repeatability",
                "translation_quote":" | ".join(dict.fromkeys(collapsed)),
                "reason":"The English source uses recurrence and independent repeatability as distinct evidence concepts, but Turkish collapses recurrence into 'tekrarlanabilirlik'.",
            })

    # Preserve explicit no-advisory decision if present in the source.
    if re.search(r"route advisory\s+NOT\s+recommended",source_en,re.IGNORECASE):
        if not re.search(r"rota\s+uyar(?:ı|isi).{0,40}(?:tavsiye\s+edilmez|önerilmez)",translation_tr,re.IGNORECASE|re.DOTALL):
            findings.append({
                "guard_id":"no_advisory_negation",
                "severity":"serious",
                "family":"translation_fidelity",
                "source_quote":"Route advisory NOT recommended",
                "translation_quote":"",
                "reason":"The explicit no-advisory decision from the English source is not preserved in Turkish.",
            })

    return findings
