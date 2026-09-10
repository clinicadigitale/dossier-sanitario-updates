from pathlib import Path
import re

ROOT = Path('android-r3')
TEST = ROOT / 'app/src/test/java/it/dossiersanitario/clinicadigitale/beta'
GRADLE = ROOT / 'app/build.gradle'
R45_NAME = '1.0.0-android-r45-year-axis-progressive-backup-test'

# R45 is the final build identity after every predecessor compatibility patch.
g = GRADLE.read_text(encoding='utf-8')
g = re.sub(r'versionCode\s+\d+', 'versionCode 45', g, count=1)
g = re.sub(r'versionName\s+[\"\'][^\"\']+[\"\']', f'versionName "{R45_NAME}"', g, count=1)
GRADLE.write_text(g, encoding='utf-8')

for p in TEST.glob('R*Test.java'):
    if p.name == 'R45YearAxisProgressiveBackupTest.java':
        continue
    s = p.read_text(encoding='utf-8')
    for n in range(17, 46):
        s = s.replace(f'versionCode {n}', 'versionCode 45')
    s = re.sub(r'1\.0\.0-android-r\d+[A-Za-z0-9._-]*', R45_NAME, s)
    s = re.sub(r'assertTrue\(gradle\.contains\("versionName .*?"\)\);', f'assertTrue(gradle.contains("{R45_NAME}"));', s)
    s = s.replace('syncInteractiveR44(activity, prefs)', 'syncInteractiveR45(activity, prefs)')
    p.write_text(s, encoding='utf-8')

# R42's axis test was intentionally redefined by R44 to expect report-date labels.
# R45 supersedes only that assertion: the axis now emits chronological calendar years.
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

print('R45 predecessor regression compatibility applied')
