#!/usr/bin/env python3
"""Atlantis bölüm özetleri için sadece stdlib kullanan doğrulayıcı."""
from pathlib import Path
import re, json, collections, sys
root = Path(__file__).resolve().parent
files = sorted(root.glob('season-*/S??E??-*.md'))
issues = []
complete = 0
for season in range(1, 6):
    subset = [f for f in files if f.parent.name == f'season-{season:02d}']
    if len(subset) != 20:
        issues.append(f'Sezon {season} dosya sayısı: {len(subset)} (beklenen 20)')
    for ep in range(1, 21):
        matches = [f for f in subset if f.name.startswith(f'S{season:02d}E{ep:02d}-')]
        if len(matches) != 1:
            issues.append(f'S{season:02d}E{ep:02d}: {len(matches)} kayıt')
for f in files:
    content = f.read_text(encoding='utf-8')
    status = re.search(r'^status:\s*([^\n]+)', content, re.M)
    status = status.group(1).strip() if status else 'missing'
    declared = re.search(r'^word_count:\s*(\d+)', content, re.M)
    declared = int(declared.group(1)) if declared else -1
    body = content.split('## Türkçe olay özeti\n\n', 1)[-1].split('\n\n## Kaynaklar', 1)[0].strip()
    count = len(body.split())
    if status == 'complete':
        complete += 1
        if not (250 <= count <= 400) or count != declared:
            issues.append(f'{f.name}: {count} kelime (meta: {declared})')
        if 'source_verified: true' not in content:
            issues.append(f'{f.name}: kaynak doğrulanmamış')
        if f'https://www.gateworld.net/atlantis/s' not in content:
            issues.append(f'{f.name}: GateWorld bağlantısı yok')
    elif status != 'pending_research':
        issues.append(f'{f.name}: geçersiz durum {status}')
result = {'expected': 100, 'files': len(files), 'complete': complete, 'pending': len(files)-complete, 'issues': issues}
print(json.dumps(result, ensure_ascii=False, indent=2))
sys.exit(1 if issues else 0)
