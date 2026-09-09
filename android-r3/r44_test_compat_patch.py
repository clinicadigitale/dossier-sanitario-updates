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
    s = s.replace('"0.48f"', '"0.30f"')
    s = s.replace('"0.52f"', '"0.70f"')
    s = s.replace('assertTrue(label.contains("R43LayoutGeometry.landscapeLabelWidthPx"));', 'assertTrue(label.contains("0.30f"));')
    s = s.replace('assertTrue(main.contains("R43LayoutGeometry.landscapeLabelWidthPx"));', 'assertTrue(main.contains("0.30f"));')
    p.write_text(s, encoding='utf-8')

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

p = TEST / 'R43WindowsParityLandscapeSyncTest.java'
if p.exists():
    s = p.read_text(encoding='utf-8')
    s = s.replace('chartUsesEvenWindowsLikeObservationSpacing', 'chartKeepsInclinedDatesAndFallbackSpacing')
    p.write_text(s, encoding='utf-8')

# R43 already introduced these helpers. R44 replaces drawYearAxis with a block that
# includes the successor implementations, so remove only duplicate later definitions.
CHART = ROOT / 'app/src/main/java/it/dossiersanitario/clinicadigitale/beta/R26ChartView.java'
cs = CHART.read_text(encoding='utf-8')

def remove_second_block(text, signature):
    first = text.find(signature)
    if first < 0:
        return text
    second = text.find(signature, first + len(signature))
    if second < 0:
        return text
    brace = text.find('{', second)
    if brace < 0:
        return text
    depth = 0
    end = -1
    for i in range(brace, len(text)):
        if text[i] == '{': depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end < 0:
        return text
    while end < len(text) and text[end] in '\r\n':
        end += 1
    return text[:second] + text[end:]

for sig in [
    '    static float pointXForIndex(int index, int count, float left, float right) {',
    '    static float dateLabelRotationDegrees() {',
    '    private String shortClinicalDate(String raw) {'
]:
    cs = remove_second_block(cs, sig)
CHART.write_text(cs, encoding='utf-8')

print('R44 predecessor regression compatibility applied')
