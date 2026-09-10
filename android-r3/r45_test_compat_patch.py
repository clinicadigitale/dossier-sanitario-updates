from pathlib import Path
import re

ROOT = Path('android-r3')
TEST = ROOT / 'app/src/test/java/it/dossiersanitario/clinicadigitale/beta'
GRADLE = ROOT / 'app/build.gradle'
R45_NAME = '1.0.0-android-r45-year-axis-progressive-backup-test'


def replace_test_method(path, method_name, replacement):
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
    if end < 0: raise SystemExit('R45 compatibility failed: unclosed ' + method_name)
    s = s[:line_start] + replacement.rstrip() + s[end:]
    p.write_text(s, encoding='utf-8')

# R45 is the final build identity after every predecessor compatibility patch.
g = GRADLE.read_text(encoding='utf-8')
g = re.sub(r'versionCode\s*(?:=\s*)?\d+', 'versionCode 45', g, count=1)
g = re.sub(r'versionName\s*(?:=\s*)?[\"\'][^\"\']+[\"\']', f'versionName "{R45_NAME}"', g, count=1)
GRADLE.write_text(g, encoding='utf-8')

for p in TEST.glob('R*Test.java'):
    s = p.read_text(encoding='utf-8')
    if p.name != 'R45YearAxisProgressiveBackupTest.java':
        s = re.sub(r'1\.0\.0-android-r\d+[A-Za-z0-9._-]*', R45_NAME, s)
        s = s.replace('syncInteractiveR44(activity, prefs)', 'syncInteractiveR45(activity, prefs)')
    p.write_text(s, encoding='utf-8')

# Historical graph assertions intentionally superseded by the R45 year-axis contract.
current_graph_math = '''    @Test public void r38GraphMathRemainsPresent() throws Exception {\n        String chart = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R26ChartView.java");\n        assertTrue(chart.contains("requestedValue(o, preferredKeys)"));\n        assertTrue(chart.contains("scaledBoundsWithReference(dataMin, dataMax, referenceLow, referenceHigh)"));\n        assertFalse(chart.contains("R26SnapshotBridge.numericValue"));\n    }'''
replace_test_method('R39ExactLabsLandscapeSyncProgressV2Test.java', 'r38GraphMathRemainsPresent()', current_graph_math)

current_graph_frozen = '''    @Test public void r38GraphFixesRemainFrozen() throws Exception {\n        String chart = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R26ChartView.java");\n        assertTrue(chart.contains("requestedValue(o, preferredKeys)"));\n        assertTrue(chart.contains("scaledBoundsWithReference(dataMin, dataMax, referenceLow, referenceHigh)"));\n        assertFalse(chart.contains("R26SnapshotBridge.numericValue"));\n    }'''
replace_test_method('R39LandscapeLabSeriesSyncProgressTest.java', 'r38GraphFixesRemainFrozen()', current_graph_frozen)

r40_axis = '''    @Test public void graphUsesClinicalDatesForHorizontalAxis() throws Exception {\n        String chart = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R26ChartView.java");\n        assertTrue(chart.contains("dateTimes(dates)"));\n        assertTrue(chart.contains("pointXForTime(times[i], tMin, tMax, left, right)"));\n        assertTrue(chart.contains("yearTicks(tMin, tMax)"));\n        assertTrue(chart.contains("String.valueOf(year)"));\n        assertFalse(chart.contains("shortClinicalDate(dates.get(i))"));\n    }'''
replace_test_method('R40GlobalParityFixTest.java', 'graphUsesClinicalDatesForHorizontalAxis()', r40_axis)

r41_axis = '''    @Test public void chartStillUsesExactRequestedSeriesAndClinicalDates() throws Exception {\n        String chart = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R26ChartView.java");\n        assertTrue(chart.contains("requestedValue(o, preferredKeys)"));\n        assertTrue(chart.contains("dateTimes(dates)"));\n        assertTrue(chart.contains("pointXForTime(times[i], tMin, tMax, left, right)"));\n        assertTrue(chart.contains("yearTicks(tMin, tMax)"));\n        assertTrue(chart.contains("sourceDocumentLabel"));\n    }'''
replace_test_method('R41RealDeviceFinalFixTest.java', 'chartStillUsesExactRequestedSeriesAndClinicalDates()', r41_axis)

# R42's axis test was intentionally redefined by R44 to expect report-date labels.
p = TEST / 'R42RealDeviceLandscapeGraphSyncFixTest.java'
if p.exists():
    s = p.read_text(encoding='utf-8')
    marker = '@Test public void clinicalDateAxisUsesInclinedLabelsWithoutDroppingDates()'
    start = s.find(marker)
    if start >= 0:
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
        if end < 0: raise SystemExit('R45 compatibility failed: R42 axis test unclosed')
        repl = '''    @Test public void clinicalDateAxisUsesInclinedYearTicksInsteadOfReportDateLabels() throws Exception {\n        String chart = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R26ChartView.java");\n        assertTrue(chart.contains("dateLabelRotationDegrees()"));\n        assertTrue(chart.contains("return -45f"));\n        assertTrue(chart.contains("yearTicks(tMin, tMax)"));\n        assertTrue(chart.contains("String.valueOf(year)"));\n        assertFalse(chart.contains("maximumLabels"));\n    }'''
        s = s[:line_start] + repl + s[end:]
        p.write_text(s, encoding='utf-8')

# Normalize every historical version test to the final build identity, including
# regex-based assertions introduced by R44.
for p in TEST.glob('R*Test.java'):
    s = p.read_text(encoding='utf-8')
    pos = 0
    while True:
        m = re.search(r'@Test public void version[A-Za-z0-9_]*\(\) throws Exception\s*\{', s[pos:])
        if not m: break
        start = pos + m.start()
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
        if end < 0: raise SystemExit('R45 compatibility failed: unclosed version test in ' + p.name)
        method_decl = s[start:s.find('{', start)].strip()
        name = re.search(r'void\s+([A-Za-z0-9_]+)', method_decl).group(1)
        repl = f'''    @Test public void {name}() throws Exception {{\n        String gradle = read("build.gradle");\n        assertTrue(gradle.contains("versionCode 45"));\n        assertTrue(gradle.contains("{R45_NAME}"));\n    }}'''
        s = s[:line_start] + repl + s[end:]
        pos = line_start + len(repl)
    p.write_text(s, encoding='utf-8')

print('R45 predecessor regression compatibility applied')
