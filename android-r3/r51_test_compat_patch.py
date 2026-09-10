from pathlib import Path

TEST = Path('android-r3/app/src/test/java/it/dossiersanitario/clinicadigitale/beta')
old_name = '1.0.0-android-r50-r47-height-sync-finalize-test'
new_name = '1.0.0-android-r51-graph-height-ticks-sync-reminder-test'
changed = 0

for p in TEST.glob('*.java'):
    s = p.read_text(encoding='utf-8')
    original = s
    s = s.replace('versionCode 50', 'versionCode 51')
    s = s.replace('versionCode = 50', 'versionCode = 51')
    s = s.replace(old_name, new_name)
    if p.name == 'R50R47HeightSyncFinalizeTest.java':
        s = s.replace('assertFalse(c.contains("setMinimumHeight(dp(400))"));', 'assertTrue(c.contains("setMinimumHeight(dp(400))"));')
    if s != original:
        p.write_text(s, encoding='utf-8')
        changed += 1

if changed < 2:
    raise SystemExit('R51 compatibility patch changed too few inherited tests: %d' % changed)
print('R51 inherited test compatibility aligned:', changed)
