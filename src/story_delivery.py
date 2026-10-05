"""Lossless delivery normalization, with proofs and no model calls."""
import hashlib
import re


def sha(text):
    return hashlib.sha256(text.encode('utf8')).hexdigest()


def normalize_marked_story(raw, scene_ids, *, encoding_provenance='utf8'):
    if not scene_ids or len(set(scene_ids)) != len(scene_ids):
        raise RuntimeError('Invalid expected scene sequence')
    if any(not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,39}', sid) for sid in scene_ids):
        raise RuntimeError('Invalid scene identifier')
    if encoding_provenance == 'latin1_decoded_utf8_sse':
        try:
            text = raw.encode('latin1').decode('utf8')
        except UnicodeError as exc:
            raise RuntimeError('Recorded encoding provenance cannot be reversed') from exc
        if text.encode('utf8').decode('latin1') != raw:
            raise RuntimeError('Encoding round-trip failed')
    elif encoding_provenance == 'utf8':
        text = raw
    else:
        raise RuntimeError('Unknown encoding provenance; do not guess')
    if '\r' in text:
        raise RuntimeError('Expected LF scene boundaries')
    marks = list(re.finditer(r'^\[\[([A-Za-z][A-Za-z0-9_-]{0,39})\]\][ \t]*$', text, re.M))
    sequence = [m[1] for m in marks]
    if not sequence or len(sequence) % len(scene_ids):
        raise RuntimeError('Incomplete scene sequence')
    count = len(sequence) // len(scene_ids)
    if sequence != list(scene_ids) * count:
        raise RuntimeError('Unexpected or reordered scene sequence')
    title = text[:marks[0].start()].strip()
    if not title or '\n' in title or '[[' in title:
        raise RuntimeError('Invalid single story title')
    starts = [0]
    for copy_index in range(1, count):
        first = marks[copy_index * len(scene_ids)]
        previous = marks[copy_index * len(scene_ids) - 1]
        boundary = text.rfind(title, previous.end(), first.start())
        if boundary < 0 or text[boundary+len(title):first.start()].strip():
            raise RuntimeError('Repeated story boundary not proven')
        starts.append(boundary)
    copies = [text[a:b].strip() for a,b in zip(starts, starts[1:]+[len(text)])]
    if not copies[0] or any(copy != copies[0] for copy in copies):
        raise RuntimeError('Distinct drafts cannot be collapsed')
    canonical = copies[0]
    return canonical, {
        'raw_sha256': sha(raw), 'decoded_sha256': sha(text),
        'encoding_provenance': encoding_provenance,
        'copy_start_offsets': starts, 'identical_copy_count': count,
        'copy_sha256': [sha(copy) for copy in copies],
        'canonical_marked_story_sha256': sha(canonical),
        'semantic_rewrite': False, 'source_delivery_had_repetition': count > 1,
        'repeat_origin': 'UNDETERMINED' if count > 1 else None,
    }
