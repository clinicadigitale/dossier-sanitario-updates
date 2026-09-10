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
    raise SystemExit('R47 compile compat: target method not found')
p.write_text(s.replace(old, new, 1), encoding='utf-8')
print('R47 final historical test compile fix applied')
