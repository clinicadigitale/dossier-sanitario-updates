from pathlib import Path

TEST = Path('android-r3/app/src/test/java/it/dossiersanitario/clinicadigitale/beta')
changed = 0
for p in TEST.glob('*.java'):
    s = p.read_text(encoding='utf-8')
    original = s
    s = s.replace('versionCode 52', 'versionCode 53')
    s = s.replace('versionCode = 52', 'versionCode = 53')
    s = s.replace('1.0.0-android-r52-all-graphs-height-test', '1.0.0-android-r53-prepare-visit-dossier-search-test')
    if s != original:
        p.write_text(s, encoding='utf-8')
        changed += 1
if changed < 1:
    raise SystemExit('R53 compatibility did not update inherited version expectations')
print('R53 inherited version expectations aligned:', changed)
