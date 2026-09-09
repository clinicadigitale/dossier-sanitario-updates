from pathlib import Path
import re

ROOT = Path('android-r3')
TEST = ROOT / 'app/src/test/java/it/dossiersanitario/clinicadigitale/beta'
GRADLE = ROOT / 'app/build.gradle'
R44_NAME = '1.0.0-android-r44-realdevice-parity-sync-test'

g = GRADLE.read_text(encoding='utf-8')
g = re.sub(r'versionCode\s+\d+', 'versionCode 44', g, count=1)
g = re.sub(r'versionName\s+[\"\'][^\"\']+[\"\']', f'versionName "{R44_NAME}"', g, count=1)
GRADLE.write_text(g, encoding='utf-8')

for p in TEST.glob('R*Test.java'):
    if p.name == 'R44RealDeviceParitySyncTest.java':
        continue
    s = p.read_text(encoding='utf-8')
    for n in range(17, 45):
        s = s.replace(f'versionCode {n}', 'versionCode 44')
    s = re.sub(r'1\.0\.0-android-r\d+[A-Za-z0-9._-]*', R44_NAME, s)
    s = re.sub(r'assertTrue\(gradle\.contains\("versionName .*?"\)\);', f'assertTrue(gradle.contains("{R44_NAME}"));', s)
    s = s.replace('syncInteractiveR43(activity, prefs)', 'syncInteractiveR44(activity, prefs)')
    s = s.replace('syncInteractiveR42(activity, prefs)', 'syncInteractiveR44(activity, prefs)')
    s = s.replace('syncInteractiveR41(activity, prefs)', 'syncInteractiveR44(activity, prefs)')
    # Landscape successor deliberately supersedes earlier 48/52 geometry.
    s = s.replace('"0.48f"', '"0.30f"')
    s = s.replace('"0.52f"', '"0.70f"')
    # R43 no longer uses the explicit pixel helper in labelValue; rotation rebuild stays authoritative.
    s = s.replace('assertTrue(label.contains("R43LayoutGeometry.landscapeLabelWidthPx"));', 'assertTrue(label.contains("0.30f"));')
    s = s.replace('assertTrue(main.contains("R43LayoutGeometry.landscapeLabelWidthPx"));', 'assertTrue(main.contains("0.30f"));')
    p.write_text(s, encoding='utf-8')

# R42 axis test was intentionally superseded in R43 by inclined full clinical dates.
p = TEST / 'R42RealDeviceLandscapeGraphSyncFixTest.java'
if p.exists():
    s = p.read_text(encoding='utf-8')
    start = s.find('    @Test public void clinicalYearAxisCannotEmitOverlappingEveryTwoYearLabelsOnNarrowPhone()')
    if start >= 0:
        end = s.find('    @Test public void allChartsStillKeepWindowsReferenceLinesAndClinicalDateAxis()', start)
        if end > start:
            repl = '''    @Test public void clinicalDateAxisUsesInclinedLabelsWithoutDroppingDates() throws Exception {\n        String chart = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R26ChartView.java");\n        assertTrue(chart.contains("dateLabelRotationDegrees()"));\n        assertTrue(chart.contains("return -45f"));\n        assertTrue(chart.contains("shortClinicalDate(dates.get(i))"));\n        assertFalse(chart.contains("maximumLabels"));\n    }\n\n'''
            s = s[:start] + repl + s[end:]
    p.write_text(s, encoding='utf-8')

# R43 graph successor restores actual-date geometry while retaining helper fallback.
p = TEST / 'R43WindowsParityLandscapeSyncTest.java'
if p.exists():
    s = p.read_text(encoding='utf-8')
    s = s.replace('chartUsesEvenWindowsLikeObservationSpacing', 'chartKeepsInclinedDatesAndFallbackSpacing')
    p.write_text(s, encoding='utf-8')

print('R44 predecessor regression compatibility applied')
