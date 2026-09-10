from pathlib import Path
import re

TEST = Path('android-r3/app/src/test/java/it/dossiersanitario/clinicadigitale/beta')
R47_NAME = '1.0.0-android-r47-sync-crash-graph-layout-test'


def replace_method(path, method_name, replacement):
    p = TEST / path
    if not p.exists(): return
    s = p.read_text(encoding='utf-8')
    marker = '@Test public void ' + method_name
    start = s.find(marker)
    if start < 0: return
    line_start = s.rfind('\n', 0, start) + 1
    brace = s.find('{', start); depth = 0; end = -1
    for i in range(brace, len(s)):
        if s[i] == '{': depth += 1
        elif s[i] == '}':
            depth -= 1
            if depth == 0: end = i + 1; break
    if end < 0: raise SystemExit('R47 compat failed: unclosed ' + method_name)
    s = s[:line_start] + replacement.rstrip() + s[end:]
    p.write_text(s, encoding='utf-8')

replace_method('R46WindowsGraphSyncPageAuditTest.java', 'allGraphsUseSharedWindowsYearAxis()', r'''    @Test public void allGraphsUseSharedWindowsYearAxis() throws Exception {
        String chart = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R26ChartView.java");
        assertTrue(chart.contains("R47GraphGeometry.ticks"));
        assertTrue(chart.contains("dateLabelRotationDegrees()"));
        assertTrue(chart.contains("String.valueOf(year)"));
        assertTrue(chart.contains("R47GraphGeometry.yearStart(tMin)"));
        assertTrue(chart.contains("R47GraphGeometry.yearEndExclusive(tMax)"));
    }''')

replace_method('R45YearAxisProgressiveBackupTest.java', 'yearAxisUsesWindowsSparseChronologicalScheme()', r'''    @Test public void yearAxisUsesResponsiveWindowsChronologicalScheme() {
        long a = R26ChartView.yearStartMillis(2003);
        long b = R26ChartView.yearStartMillis(2026) + 86400000L;
        assertTrue(R47GraphGeometry.yearStart(a) <= a);
        assertTrue(R47GraphGeometry.yearEndExclusive(b) > b);
        int[] years = R47GraphGeometry.ticks(2003, 2026, 1200f, 1f);
        assertEquals(2003, years[0]);
        assertEquals(2026, years[years.length - 1]);
    }''')

p = TEST / 'R45YearAxisProgressiveBackupTest.java'
if p.exists():
    s = p.read_text(encoding='utf-8')
    s = s.replace('assertTrue(axis.contains("R46GraphMath.windowsYearTicks(first, last)"));',
                  'assertTrue(axis.contains("R47GraphGeometry.ticks"));')
    p.write_text(s, encoding='utf-8')

# R46 page audit remains valid. Only package identity moves to R47.
for p in TEST.glob('R*Test.java'):
    s = p.read_text(encoding='utf-8')
    s = s.replace('1.0.0-android-r46-windows-graph-sync-page-audit-test', R47_NAME)
    s = re.sub(r'versionCode\\s*\\(?:=\\s*\\?\\)\\?46', r'versionCode\\s*(?:=\\s*)?47', s)
    s = s.replace('versionCode 46', 'versionCode 47')
    s = s.replace('versionCode\\s*(?:=\\s*)?46', 'versionCode\\s*(?:=\\s*)?47')
    s = s.replace('versionIsR46', 'versionIsR47')
    p.write_text(s, encoding='utf-8')

print('R47 predecessor regression compatibility applied')
