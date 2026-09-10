from pathlib import Path
import re

TEST = Path('android-r3/app/src/test/java/it/dossiersanitario/clinicadigitale/beta')
R46_NAME = '1.0.0-android-r46-windows-graph-sync-page-audit-test'


def replace_method(path, method_name, replacement):
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
    if end < 0: raise SystemExit('R46 compatibility failed: unclosed ' + method_name)
    s = s[:line_start] + replacement.rstrip() + s[end:]
    p.write_text(s, encoding='utf-8')

replace_method('R45YearAxisProgressiveBackupTest.java', 'yearAxisContainsEveryCalendarYearInChronologicalOrder()', r'''    @Test public void yearAxisUsesWindowsSparseChronologicalScheme() {
        long a = R26ChartView.yearStartMillis(2003);
        long b = R26ChartView.yearStartMillis(2026) + 86400000L;
        int[] years = R26ChartView.yearTicks(a, b);
        assertArrayEquals(new int[]{2003,2005,2007,2009,2011,2013,2015,2017,2019,2021,2023,2025,2026}, years);
        assertTrue(R26ChartView.pointXForTime(R26ChartView.yearStartMillis(2011), a, b, 100f, 900f) <
                R26ChartView.pointXForTime(R26ChartView.yearStartMillis(2012), a, b, 100f, 900f));
    }''')

replace_method('R45YearAxisProgressiveBackupTest.java', 'decryptProgressCountsEncryptedBytesNotOnlyProducedPlaintext()', r'''    @Test public void decryptProgressUsesStreamingCipherBytes() throws Exception {
        String decryptor = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R46Dsl5Decryptor.java");
        assertTrue(decryptor.contains("cipher.update(buffer, 0, n)"));
        assertTrue(decryptor.contains("progress.onBytes(done, total)"));
        String cloud = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R12CloudManager.java");
        assertTrue(cloud.contains("R46Dsl5Decryptor.decrypt"));
        assertTrue(cloud.contains("R46ProgressMath.percent(read, total, 46, 75)"));
        assertTrue(cloud.contains("R46ProgressMath.importPercent(done, total)"));
    }''')

replace_method('R45YearAxisProgressiveBackupTest.java', 'progressMathAdvancesOnePercentAtATimeWhenBytesAdvance()', r'''    @Test public void progressMathAdvancesOnePercentAtATimeWhenBytesAdvance() {
        assertEquals(46, R46ProgressMath.percent(0, 100, 46, 75));
        assertEquals(75, R46ProgressMath.percent(100, 100, 46, 75));
        int previous = 46;
        boolean sawIncrementOfOne = false;
        for (int done = 0; done <= 1000; done++) {
            int now = R46ProgressMath.percent(done, 1000, 46, 75);
            if (now - previous == 1) sawIncrementOfOne = true;
            assertTrue(now >= previous);
            assertTrue(now - previous <= 1);
            previous = now;
        }
        assertTrue(sawIncrementOfOne);
    }''')

# R45 axis source assertion remains valid except its helper now delegates to R46.
p = TEST / 'R45YearAxisProgressiveBackupTest.java'
if p.exists():
    s = p.read_text(encoding='utf-8')
    s = s.replace('assertFalse(axis.contains("maximumLabels"));', 'assertTrue(axis.contains("R46GraphMath.windowsYearTicks(first, last)"));')
    p.write_text(s, encoding='utf-8')

# Normalize historical package identity tests to final R46 identity.
for p in TEST.glob('R*Test.java'):
    if p.name == 'R46WindowsGraphSyncPageAuditTest.java':
        continue
    s = p.read_text(encoding='utf-8')
    s = re.sub(r'1\.0\.0-android-r45-year-axis-progressive-backup-test', R46_NAME, s)
    s = re.sub(r'versionCode\\s*\\(?:=\\s*\\?\\)\\?45', r'versionCode\\s*(?:=\\s*)?46', s)
    s = s.replace('versionCode 45', 'versionCode 46')
    s = s.replace('versionCode\\s*(?:=\\s*)?45', 'versionCode\\s*(?:=\\s*)?46')
    s = s.replace('versionIsR45', 'versionIsR46')
    p.write_text(s, encoding='utf-8')

print('R46 predecessor regression compatibility applied')
