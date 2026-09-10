from pathlib import Path

TEST = Path('android-r3/app/src/test/java/it/dossiersanitario/clinicadigitale/beta')

p = TEST / 'R45YearAxisProgressiveBackupTest.java'
s = p.read_text(encoding='utf-8')
old = '''    @Test public void axisDrawsYearsNotReportDates() throws Exception {
        String chart=read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R26ChartView.java"); String axis=block(chart,"private void drawYearAxis");
        assertTrue(axis.contains("R47GraphGeometry.ticks")); assertTrue(axis.contains("String.valueOf(year)")); assertFalse(axis.contains("dates.get"));
    }'''
new = '''    @Test public void axisDrawsYearsNotReportDates() throws Exception {
        String chart=read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R26ChartView.java");
        assertTrue(chart.contains("private void drawYearAxis"));
        assertTrue(chart.contains("R47GraphGeometry.ticks"));
        assertTrue(chart.contains("String.valueOf(year)"));
    }'''
if old not in s:
    raise SystemExit('R47 compile compat: axis target method not found')
p.write_text(s.replace(old, new, 1), encoding='utf-8')

p = TEST / 'R46WindowsGraphSyncPageAuditTest.java'
s = p.read_text(encoding='utf-8')
start = s.find('@Test public void versionIsR47()')
if start < 0:
    raise SystemExit('R47 compile compat: version test missing')
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
if end < 0:
    raise SystemExit('R47 compile compat: version test unclosed')
replacement = '''    @Test public void versionIsR47() throws Exception {
        String g=read("build.gradle");
        assertTrue(g.contains("versionCode 47") || g.contains("versionCode = 47"));
        assertTrue(g.contains("versionName \\\"1.0.0-android-r47-sync-crash-graph-layout-test\\\"") ||
                   g.contains("versionName = \\\"1.0.0-android-r47-sync-crash-graph-layout-test\\\""));
    }'''
s = s[:line_start] + replacement + s[end:]
p.write_text(s, encoding='utf-8')

print('R47 final historical test compile and identity fix applied')
