from pathlib import Path

TEST = Path('android-r3/app/src/test/java/it/dossiersanitario/clinicadigitale/beta')
changed = 0
for p in TEST.glob('*.java'):
    s = p.read_text(encoding='utf-8')
    original = s
    s = s.replace('versionCode 51', 'versionCode 52')
    s = s.replace('versionCode = 51', 'versionCode = 52')
    s = s.replace('1.0.0-android-r51-graph-height-ticks-sync-reminder-test', '1.0.0-android-r52-all-graphs-height-test')
    s = s.replace('setMinimumHeight(dp(400))', 'setMinimumHeight(dp(430))')
    if s != original:
        p.write_text(s, encoding='utf-8')
        changed += 1
if changed < 2:
    raise SystemExit('R52 compatibility changed too few inherited tests: %d' % changed)
print('R52 inherited test compatibility aligned:', changed)
