from pathlib import Path

TEST = Path('android-r3/app/src/test/java/it/dossiersanitario/clinicadigitale/beta')


def patch(name, replacements):
    p = TEST / name
    s = p.read_text(encoding='utf-8')
    for old, new in replacements:
        if old not in s:
            raise SystemExit(f'R30 test compatibility failed: {name}: {old}')
        s = s.replace(old, new)
    p.write_text(s, encoding='utf-8')

version_replacements = [
    ('versionCode 29', 'versionCode 30'),
    ("versionName '1.0.0-android-r29-progress-crashguard-test'", "versionName '1.0.0-android-r30-bounded-import-test'"),
]

patch('R26NearFinalTest.java', version_replacements)
patch('R27CompleteWindowsImportTest.java', [
    ('assertTrue(cloud.contains("R27ExactWindows.importSnapshot"));', 'assertTrue(cloud.contains("R30BoundedWindows.importSnapshot"));'),
    *version_replacements,
])
patch('R28StartupAsyncTest.java', [
    ('assertTrue(cloud.contains("R27ExactWindows.importSnapshot"));', 'assertTrue(cloud.contains("R30BoundedWindows.importSnapshot"));'),
    *version_replacements,
])
patch('R29ProgressCrashGuardTest.java', version_replacements)
print('R30 prior regression tests aligned')
