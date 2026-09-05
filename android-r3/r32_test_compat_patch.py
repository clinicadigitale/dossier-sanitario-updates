from pathlib import Path

TEST = Path('android-r3/app/src/test/java/it/dossiersanitario/clinicadigitale/beta')


def patch(name):
    p = TEST / name
    s = p.read_text(encoding='utf-8')
    if 'versionCode 31' not in s or "versionName '1.0.0-android-r31-mobile-parity-test'" not in s:
        raise SystemExit(f'R32 compatibility failed: {name}')
    s = s.replace('versionCode 31', 'versionCode 32')
    s = s.replace("versionName '1.0.0-android-r31-mobile-parity-test'", "versionName '1.0.0-android-r32-ordering-monitor-test'")
    p.write_text(s, encoding='utf-8')

for name in [
    'R26NearFinalTest.java',
    'R27CompleteWindowsImportTest.java',
    'R28StartupAsyncTest.java',
    'R29ProgressCrashGuardTest.java',
    'R30BoundedImportTest.java',
    'R31MobileParityTest.java',
]:
    patch(name)
print('R32 prior regression tests aligned')
