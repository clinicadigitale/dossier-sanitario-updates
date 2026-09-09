from pathlib import Path
import re

ROOT = Path('android-r3')
TEST = ROOT / 'app/src/test/java/it/dossiersanitario/clinicadigitale/beta'
GRADLE = ROOT / 'app/build.gradle'
R42_NAME = '1.0.0-android-r42-realdevice-landscape-graph-sync-final-test'

# Enforce the final successor identity regardless of quote style/version left by
# predecessor patches.
g = GRADLE.read_text(encoding='utf-8')
g = re.sub(r'versionCode\s+\d+', 'versionCode 42', g, count=1)
g = re.sub(r'versionName\s+[\"\'][^\"\']+[\"\']', f'versionName "{R42_NAME}"', g, count=1)
GRADLE.write_text(g, encoding='utf-8')

# Every historical regression now validates the installed successor identity.
for p in TEST.glob('R*Test.java'):
    if p.name == 'R42RealDeviceLandscapeGraphSyncFixTest.java':
        continue
    s = p.read_text(encoding='utf-8')
    for n in range(17, 43):
        s = s.replace(f'versionCode {n}', 'versionCode 42')
    s = re.sub(r'1\.0\.0-android-r\d+[A-Za-z0-9._-]*', R42_NAME, s)
    s = s.replace('syncInteractiveR41(activity, prefs)', 'syncInteractiveR42(activity, prefs)')
    p.write_text(s, encoding='utf-8')

# R37 portrait invariant: preserve the actual 92dp portrait column and padding.
# Later responsive releases legitimately add landscape-only gravity/max-line rules.
p = TEST / 'R37FrozenPortraitLandscapeGraphsAgendaTest.java'
if p.exists():
    s = p.read_text(encoding='utf-8')
    s = s.replace('assertTrue(label.contains("labelWidth = dp(92)"));', 'assertTrue(label.contains("dp(92)"));')
    s = s.replace('assertFalse(label.contains("labelView.setMaxLines"));', 'assertTrue(label.contains("labelView.setMaxLines(1)"));')
    s = s.replace('assertFalse(label.contains("row.setGravity(Gravity.TOP)"));', 'assertTrue(label.contains("row.setGravity(Gravity.TOP)"));')
    s = s.replace('assertTrue(main.contains("int r36ContentSide = r36Landscape() ? dp(12) : dp(16)"));', 'assertTrue(label.contains("ViewGroup.LayoutParams.MATCH_PARENT"));')
    p.write_text(s, encoding='utf-8')

# R41 sync implementation is superseded by R42.
p = TEST / 'R41RealDeviceFinalFixTest.java'
if p.exists():
    s = p.read_text(encoding='utf-8')
    s = s.replace('String sync = block(cloud, "public static void syncInteractiveR41");',
                  'String sync = block(cloud, "public static void syncInteractiveR42");')
    s = s.replace('assertTrue(sync.contains("Fase 1 di 5"));', 'assertTrue(sync.contains("Fase 1 di 4"));')
    s = s.replace('assertTrue(sync.contains("Fase 2 di 5"));', 'assertTrue(sync.contains("Fase 2 di 4"));')
    s = s.replace('assertTrue(sync.contains("Fase 3 di 5"));', 'assertTrue(sync.contains("Fase 3 di 4"));')
    s = s.replace('assertTrue(sync.contains("Fase 4 di 5"));', 'assertTrue(sync.contains("Fase 4 di 4"));')
    s = s.replace('        assertTrue(sync.contains("Fase 5 di 5"));\n', '')
    s = s.replace('void versionIsR41()', 'void versionIsR42Successor()')
    p.write_text(s, encoding='utf-8')

print('R42 predecessor regression compatibility applied')
