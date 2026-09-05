from pathlib import Path

TEST = Path('android-r3/app/src/test/java/it/dossiersanitario/clinicadigitale/beta')


def patch(name):
    p = TEST / name
    s = p.read_text(encoding='utf-8')
    if 'versionCode 30' not in s or "versionName '1.0.0-android-r30-bounded-import-test'" not in s:
        raise SystemExit(f'R31 compatibility failed: {name}')
    s = s.replace('versionCode 30', 'versionCode 31')
    s = s.replace("versionName '1.0.0-android-r30-bounded-import-test'", "versionName '1.0.0-android-r31-mobile-parity-test'")
    p.write_text(s, encoding='utf-8')

for name in [
    'R26NearFinalTest.java',
    'R27CompleteWindowsImportTest.java',
    'R28StartupAsyncTest.java',
    'R29ProgressCrashGuardTest.java',
    'R30BoundedImportTest.java',
]:
    patch(name)
print('R31 prior regression tests aligned')
