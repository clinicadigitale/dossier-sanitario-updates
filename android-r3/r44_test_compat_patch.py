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

# Replace only historical landscape geometry tests that are intentionally superseded by
# the user's explicit R44 requirement: 30% label column, 70% value column, portrait 92dp.
def replace_test_method(path, method_name):
    p = TEST / path
    if not p.exists(): return
    s = p.read_text(encoding='utf-8')
    marker = '@Test public void ' + method_name
    start = s.find(marker)
    if start < 0: return
    line_start = s.rfind('\n', 0, start) + 1
    brace = s.find('{', start)
    depth = 0
    end = -1
    for i in range(brace, len(s)):
        if s[i] == '{': depth += 1
        elif s[i] == '}':
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end < 0: raise SystemExit('Unclosed historical test ' + method_name)
    replacement = '''    @Test public void %s() throws Exception {\n        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");\n        String label = block(main, "private LinearLayout labelValue");\n        assertTrue(label.contains("r36Landscape()"));\n        assertTrue(label.contains("0.30f"));\n        assertTrue(label.contains("0.70f"));\n        assertTrue(label.contains("dp(92)"));\n        assertTrue(label.contains("labelView.setSingleLine(true)"));\n        assertTrue(main.contains("onConfigurationChanged(Configuration newConfig)"));\n        assertTrue(main.contains("renderSection(currentSection)"));\n    }''' % method_name
    s = s[:line_start] + replacement + s[end:]
    p.write_text(s, encoding='utf-8')

historical_landscape_tests = {
    'R36SyncResponsiveGraphsAgendaRemindersTest.java': ['landscapeUsesWiderResponsiveLabelColumnsAcrossAllLabelValueSections'],
    'R37FrozenPortraitLandscapeGraphsAgendaTest.java': ['portraitLabelGeometryIsRestoredToFrozenR34R35Baseline','landscapeLabelColumnIsAlmostDoubleAndSingleLine'],
    'R38GraphScaleLandscapeWidthTest.java': ['landscapeColumnIsReallyWiderWhilePortraitStaysFrozen'],
    'R39ExactLabsLandscapeSyncProgressV2Test.java': ['landscapeOnlyUsesWideSingleLineFirstColumn'],
    'R39ExactLabsLandscapeSyncProgressV3Test.java': ['portraitFrozenLandscapeWideSingleLine'],
    'R39LandscapeLabSeriesSyncProgressTest.java': ['portraitRemainsFrozenAndLandscapeLabelsAreOneLine'],
    'R40GlobalParityFixTest.java': ['everyStandardSectionRowUsesOneGlobalLandscapeRuleAndPortraitStaysFrozen'],
    'R41RealDeviceFinalFixTest.java': ['landscapeRuleIsGlobalWeightBasedAndPortraitRemains92dp'],
    'R42RealDeviceLandscapeGraphSyncFixTest.java': ['emergencyAndEveryStandardRowActuallyFillLandscapeCardWidth'],
}
for file_name, methods in historical_landscape_tests.items():
    for method in methods: replace_test_method(file_name, method)

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

CHART = ROOT / 'app/src/main/java/it/dossiersanitario/clinicadigitale/beta/R26ChartView.java'
cs = CHART.read_text(encoding='utf-8')

def remove_second_block(text, signature):
    first = text.find(signature)
    if first < 0: return text
    second = text.find(signature, first + len(signature))
    if second < 0: return text
    brace = text.find('{', second)
    if brace < 0: return text
    depth = 0
    end = -1
    for i in range(brace, len(text)):
        if text[i] == '{': depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end < 0: return text
    while end < len(text) and text[end] in '\r\n': end += 1
    return text[:second] + text[end:]

for sig in [
    '    static float pointXForIndex(int index, int count, float left, float right) {',
    '    static float dateLabelRotationDegrees() {',
    '    private String shortClinicalDate(String raw) {'
]:
    cs = remove_second_block(cs, sig)
CHART.write_text(cs, encoding='utf-8')

print('R44 predecessor regression compatibility applied')
