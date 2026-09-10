from pathlib import Path

TEST = Path('android-r3/app/src/test/java/it/dossiersanitario/clinicadigitale/beta')
old_name = '1.0.0-android-r47-sync-crash-graph-layout-test'
new_name = '1.0.0-android-r50-r47-height-sync-finalize-test'

changed = 0
for p in TEST.glob('*.java'):
    s = p.read_text(encoding='utf-8')
    original = s
    s = s.replace('versionCode 47', 'versionCode 50')
    s = s.replace('versionCode = 47', 'versionCode = 50')
    s = s.replace(old_name, new_name)
    if p.name == 'R47SyncCrashGraphLayoutTest.java':
        s = s.replace('process.waitFor(2, TimeUnit.MINUTES)', 'process.waitFor(1, TimeUnit.SECONDS)')
    if s != original:
        p.write_text(s, encoding='utf-8')
        changed += 1

if changed < 2:
    raise SystemExit('R50 compatibility patch changed too few inherited tests: %d' % changed)
print('R50 inherited R47 test compatibility aligned:', changed)
