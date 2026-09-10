from pathlib import Path
import re

TEST=Path('android-r3/app/src/test/java/it/dossiersanitario/clinicadigitale/beta')
NEW='1.0.0-android-r48-full-profile-graph-sync-audit-test'


def replace_method(path,name,body):
    p=TEST/path
    if not p.exists(): return
    s=p.read_text(encoding='utf-8'); marker='@Test public void '+name; start=s.find(marker)
    if start<0: return
    line=s.rfind('\n',0,start)+1; brace=s.find('{',start); depth=0; end=-1
    for i in range(brace,len(s)):
        if s[i]=='{': depth+=1
        elif s[i]=='}':
            depth-=1
            if depth==0: end=i+1; break
    if end<0: raise SystemExit('R48 compat unclosed '+name)
    p.write_text(s[:line]+body.rstrip()+s[end:],encoding='utf-8')

replace_method('R47SyncCrashGraphLayoutTest.java','graphReservesSeparateAxisAndLegendSpace()',r'''    @Test public void graphReservesSeparateAxisAndLegendSpace() throws Exception {
        String chart=read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R26ChartView.java");
        assertTrue(chart.contains("hasReference ? 122 : 98"));
        assertTrue(chart.contains("bottom + dp(54)"));
        assertTrue(chart.contains("float left = dp(66)"));
        assertTrue(chart.contains("dp(30), (top + bottom) / 2f"));
    }''')

replace_method('R42RealDeviceLandscapeGraphSyncFixTest.java','clinicalDateAxisUsesInclinedYearTicksInsteadOfReportDateLabels()',r'''    @Test public void clinicalDateAxisUsesInclinedYearTicksInsteadOfReportDateLabels() throws Exception {
        String chart=read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R26ChartView.java"); String axis=block(chart,"private void drawYearAxis");
        assertTrue(axis.contains("R46GraphMath.windowsYearTicks(firstYear, lastYear)")); assertTrue(axis.contains("dateLabelRotationDegrees()")); assertTrue(axis.contains("String.valueOf(year)")); assertFalse(axis.contains("shortClinicalDate"));
    }''')
replace_method('R42RealDeviceLandscapeGraphSyncFixTest.java','clinicalYearAxisCannotEmitOverlappingEveryTwoYearLabelsOnNarrowPhone()',r'''    @Test public void clinicalYearAxisCannotEmitOverlappingEveryTwoYearLabelsOnNarrowPhone() throws Exception {
        int[] years=R46GraphMath.windowsYearTicks(2003,2026); assertArrayEquals(new int[]{2003,2005,2007,2009,2011,2013,2015,2017,2019,2021,2023,2025,2026},years);
    }''')
replace_method('R45YearAxisProgressiveBackupTest.java','axisDrawsYearsNotReportDates()',r'''    @Test public void axisDrawsYearsNotReportDates() throws Exception {
        String chart=read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R26ChartView.java");
        assertTrue(chart.contains("private void drawYearAxis"));
        assertTrue(chart.contains("R46GraphMath.windowsYearTicks(firstYear, lastYear)"));
        assertTrue(chart.contains("String.valueOf(year)"));
    }''')
replace_method('R45YearAxisProgressiveBackupTest.java','yearAxisUsesWindowsSparseChronologicalScheme()',r'''    @Test public void yearAxisUsesWindowsSparseChronologicalScheme() {
        assertArrayEquals(new int[]{2003,2005,2007,2009,2011,2013,2015,2017,2019,2021,2023,2025,2026},R46GraphMath.windowsYearTicks(2003,2026));
    }''')
replace_method('R44RealDeviceParitySyncTest.java','valueSelectorParameterDiscoveryIsSinglePass()',r'''    @Test public void valueSelectorParameterDiscoveryIsSinglePass() throws Exception {
        String series = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R40ClinicalSeries.java");
        int start = series.indexOf("static JSONArray availableLabParameters");
        int end = series.indexOf("static JSONArray labSeries", start);
        assertTrue(start >= 0 && end > start);
        String block = series.substring(start, end);
        assertFalse(block.contains("labSeries(prefs"));
        assertTrue(block.contains("R27ExactWindows.activeProfileId(prefs)"));
        assertTrue(block.contains("R27ExactWindows.documentsForProfile(prefs, profileId)"));
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        assertTrue(main.contains("JSONArray labs = R40ClinicalSeries.availableLabParameters(prefs)"));
    }''')
replace_method('R45YearAxisProgressiveBackupTest.java','decryptProgressCountsEncryptedBytesNotOnlyProducedPlaintext()',r'''    @Test public void decryptProgressCountsEncryptedBytesNotOnlyProducedPlaintext() throws Exception {
        String crypto = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R22StreamingDsl5.java");
        assertTrue(crypto.contains("GCMBlockCipher"));
        assertTrue(crypto.contains("cipher.processBytes"));
        assertTrue(crypto.contains("cipher.doFinal"));
        assertTrue(crypto.contains("progress.onProgress"));
        String cloud = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R12CloudManager.java");
        assertTrue(cloud.contains("R22StreamingDsl5.decryptVerified(encryptedPart, plainZip, recovery"));
        assertTrue(cloud.contains("R45ProgressMath.percent(encryptedPart.length(), latest.size, 20, 40)"));
        assertTrue(cloud.contains("R45ProgressMath.importPercent(done, total)"));
    }''')
replace_method('R46WindowsGraphSyncPageAuditTest.java','allGraphsUseSharedWindowsYearAxis()',r'''    @Test public void allGraphsUseSharedWindowsYearAxis() throws Exception {
        String chart=read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R26ChartView.java"); assertTrue(chart.contains("R46GraphMath.windowsYearTicks(firstYear, lastYear)")); assertTrue(chart.contains("dateLabelRotationDegrees()"));
    }''')
replace_method('R46WindowsGraphSyncPageAuditTest.java','decryptIsTrueStreamingAndProgressive()',r'''    @Test public void decryptIsTrueStreamingAndProgressive() throws Exception {
        String d=read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R22StreamingDsl5.java"); assertTrue(d.contains("GCMBlockCipher")); assertTrue(d.contains("cipher.processBytes")); assertTrue(d.contains("cipher.doFinal"));
        String c=read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R12CloudManager.java"); assertTrue(c.contains("R22StreamingDsl5.decryptVerified")); assertTrue(c.contains("R47RcloneTransfer.download"));
    }''')
replace_method('R46WindowsGraphSyncPageAuditTest.java','versionIsR47()',r'''    @Test public void versionIsR48() throws Exception {
        String g=read("build.gradle"); assertTrue(g.contains("versionCode 48")); assertTrue(g.contains("1.0.0-android-r48-full-profile-graph-sync-audit-test"));
    }''')

for p in TEST.glob('R*Test.java'):
    s=p.read_text(encoding='utf-8')
    s=s.replace('1.0.0-android-r47-sync-crash-graph-layout-test',NEW)
    s=s.replace('versionCode 47','versionCode 48')
    s=s.replace('versionIsR47','versionIsR48')
    p.write_text(s,encoding='utf-8')

exec(Path('android-r3/r48_final_compat_patch.py').read_text(encoding='utf-8'))
print('R48 historical regressions aligned only for graph, profile scan, decrypt and identity supersessions')
