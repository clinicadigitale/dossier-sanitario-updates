from pathlib import Path
import re

BASE = Path('android-r3/app/src/main/java/it/dossiersanitario/clinicadigitale/beta')
TEST = Path('android-r3/app/src/test/java/it/dossiersanitario/clinicadigitale/beta')
R47_NAME = '1.0.0-android-r47-sync-crash-graph-layout-test'

# Keep touch hit-testing on exactly the same full-calendar-year domain used to draw points.
chart_path = BASE / 'R26ChartView.java'
chart = chart_path.read_text(encoding='utf-8')
touch_pos = chart.find('    @Override public boolean onTouchEvent(android.view.MotionEvent event) {')
if touch_pos < 0: raise SystemExit('R47 compat failed: touch handler missing')
touch = chart[touch_pos:]
old = '        boolean dated = tMin != Long.MAX_VALUE && tMax > tMin;\n\n        int nearest = -1;'
new = '        boolean dated = tMin != Long.MAX_VALUE && tMax >= tMin;\n        long axisMin = dated ? R47GraphGeometry.yearStart(tMin) : tMin;\n        long axisMax = dated ? R47GraphGeometry.yearEndExclusive(tMax) : tMax;\n        if (dated && axisMax <= axisMin) axisMax = axisMin + 1L;\n\n        int nearest = -1;'
if old not in touch: raise SystemExit('R47 compat failed: touch geometry point missing')
chart = chart[:touch_pos] + touch.replace(old, new, 1)
chart_path.write_text(chart, encoding='utf-8')

# Bounded-memory rclone output reader with a real wall-clock timeout.
(BASE / 'R47RcloneTransfer.java').write_text(r'''package it.dossiersanitario.clinicadigitale.beta;
import android.content.Context;
import java.io.BufferedReader;
import java.io.File;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.TimeUnit;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

final class R47RcloneTransfer {
    interface Progress { void onPercent(int percent); }
    private static final Pattern PERCENT = Pattern.compile("(?:^|\\s)(\\d{1,3})%(?:,|\\s|$)");
    private R47RcloneTransfer() {}
    static void download(Context context, String remote, File local, Progress progress) throws Exception {
        File parent = local.getParentFile();
        if (parent != null && !parent.exists() && !parent.mkdirs()) throw new Exception("Impossibile preparare la cartella locale.");
        File exe = new File(context.getApplicationInfo().nativeLibraryDir, "librclone.so");
        if (!exe.isFile()) throw new Exception("Connettore cloud Android non disponibile in questa build.");
        List<String> command = new ArrayList<>();
        command.add(exe.getAbsolutePath()); command.add("copyto"); command.add(remote); command.add(local.getAbsolutePath());
        command.add("--config"); command.add(R12Rclone.configFile(context).getAbsolutePath());
        command.add("--transfers"); command.add("1"); command.add("--checkers"); command.add("1");
        command.add("--buffer-size"); command.add("512K"); command.add("--multi-thread-streams"); command.add("1");
        command.add("--retries"); command.add("2"); command.add("--low-level-retries"); command.add("4");
        command.add("--contimeout"); command.add("15s"); command.add("--timeout"); command.add("60s");
        command.add("--stats"); command.add("1s"); command.add("--stats-one-line"); command.add("--log-level"); command.add("NOTICE");
        ProcessBuilder builder = new ProcessBuilder(command); builder.redirectErrorStream(true);
        builder.environment().put("TMPDIR", context.getCacheDir().getAbsolutePath()); builder.environment().put("HOME", context.getFilesDir().getAbsolutePath());
        Process process = builder.start();
        ArrayDeque<String> tail = new ArrayDeque<>(); int[] last = new int[]{-1};
        Thread reader = new Thread(() -> {
            try (BufferedReader br = new BufferedReader(new InputStreamReader(process.getInputStream(), StandardCharsets.UTF_8))) {
                String line;
                while ((line = br.readLine()) != null) {
                    synchronized (tail) { if (tail.size() >= 30) tail.removeFirst(); tail.addLast(line); }
                    Matcher m = PERCENT.matcher(line); int seen = -1; while (m.find()) seen = Integer.parseInt(m.group(1));
                    if (seen >= 0) { seen = Math.max(0, Math.min(100, seen)); if (seen > last[0]) { last[0] = seen; if (progress != null) progress.onPercent(seen); } }
                }
            } catch (Exception ignored) {}
        }, "clinica-r47-rclone-output");
        reader.start();
        boolean finished;
        try { finished = process.waitFor(2, TimeUnit.MINUTES); }
        catch (InterruptedException e) { process.destroyForcibly(); Thread.currentThread().interrupt(); throw new Exception("Sincronizzazione interrotta."); }
        if (!finished) { process.destroyForcibly(); try { reader.join(2000L); } catch (InterruptedException e) { Thread.currentThread().interrupt(); } throw new Exception("Download cloud fermo oltre il tempo massimo."); }
        try { reader.join(2000L); } catch (InterruptedException e) { Thread.currentThread().interrupt(); }
        if (process.exitValue() != 0) {
            StringBuilder b = new StringBuilder(); synchronized (tail) { for (String line : tail) b.append(line).append('\n'); }
            String text = b.toString().trim(); if (text.length() > 900) text = text.substring(text.length() - 900);
            throw new Exception(text.isEmpty() ? "Download cloud non riuscito." : text);
        }
        if (!local.isFile() || local.length() <= 0L) throw new Exception("Download cloud non completato.");
        if (progress != null) progress.onPercent(100);
    }
}
''', encoding='utf-8')


def replace_method(path, name, body):
    p = TEST / path
    if not p.exists(): return False
    s = p.read_text(encoding='utf-8'); marker='@Test public void '+name; start=s.find(marker)
    if start < 0: return False
    line=s.rfind('\n',0,start)+1; brace=s.find('{',start); depth=0; end=-1
    for i in range(brace,len(s)):
        if s[i]=='{': depth+=1
        elif s[i]=='}':
            depth-=1
            if depth==0: end=i+1; break
    if end < 0: raise SystemExit('R47 compat unclosed '+name)
    p.write_text(s[:line]+body.rstrip()+s[end:],encoding='utf-8'); return True

# Historical tests are preserved but rewritten only where R47 intentionally supersedes their implementation details.
replace_method('R40GlobalParityFixTest.java','graphUsesClinicalDatesForHorizontalAxis()',r'''    @Test public void graphUsesClinicalDatesForHorizontalAxis() throws Exception {
        String chart=read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R26ChartView.java");
        assertTrue(chart.contains("dateTimes(dates)")); assertTrue(chart.contains("pointXForTime(times[i], axisMin, axisMax"));
        assertTrue(chart.contains("R47GraphGeometry.yearStart(tMin)")); assertTrue(chart.contains("R47GraphGeometry.yearEndExclusive(tMax)"));
    }''')
replace_method('R41RealDeviceFinalFixTest.java','chartStillUsesExactRequestedSeriesAndClinicalDates()',r'''    @Test public void chartStillUsesExactRequestedSeriesAndClinicalDates() throws Exception {
        String chart=read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R26ChartView.java");
        assertTrue(chart.contains("requestedValue(o, preferredKeys)")); assertTrue(chart.contains("dateTimes(dates)")); assertTrue(chart.contains("pointXForTime(times[i], axisMin, axisMax"));
        String main=read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java"); String series=block(main,"private JSONArray r31SeriesForChoice"); assertTrue(series.contains("R40ClinicalSeries.labSeries"));
    }''')
for name in ['clinicalDateAxisUsesInclinedYearTicksInsteadOfReportDateLabels()','clinicalYearAxisCannotEmitOverlappingEveryTwoYearLabelsOnNarrowPhone()']:
    replace_method('R42RealDeviceLandscapeGraphSyncFixTest.java',name,r'''    @Test public void clinicalDateAxisUsesInclinedYearTicksInsteadOfReportDateLabels() throws Exception {
        String chart=read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R26ChartView.java"); String axis=block(chart,"private void drawYearAxis");
        assertTrue(axis.contains("R47GraphGeometry.ticks")); assertTrue(axis.contains("dateLabelRotationDegrees()")); assertTrue(axis.contains("String.valueOf(year)"));
        assertFalse(axis.contains("shortClinicalDate"));
    }''')
replace_method('R44RealDeviceParitySyncTest.java','graphUsesWindowsTimeProportionalGeometryNotEqualObservationSpacing()',r'''    @Test public void graphUsesWindowsTimeProportionalGeometryNotEqualObservationSpacing() throws Exception {
        String chart=read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R26ChartView.java");
        assertTrue(chart.contains("pointXForTime(times[i], axisMin, axisMax")); assertTrue(chart.contains("R47GraphGeometry.yearStart(tMin)"));
    }''')
replace_method('R45YearAxisProgressiveBackupTest.java','axisDrawsYearsNotReportDates()',r'''    @Test public void axisDrawsYearsNotReportDates() throws Exception {
        String chart=read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R26ChartView.java"); String axis=block(chart,"private void drawYearAxis");
        assertTrue(axis.contains("R47GraphGeometry.ticks")); assertTrue(axis.contains("String.valueOf(year)")); assertFalse(axis.contains("dates.get"));
    }''')
replace_method('R45YearAxisProgressiveBackupTest.java','yearAxisUsesWindowsSparseChronologicalScheme()',r'''    @Test public void yearAxisUsesWindowsSparseChronologicalScheme() {
        int[] years=R47GraphGeometry.ticks(2003,2026,1200f,1f); assertEquals(2003,years[0]); assertEquals(2026,years[years.length-1]);
        for(int i=1;i<years.length;i++) assertTrue(years[i]>years[i-1]);
    }''')
replace_method('R46WindowsGraphSyncPageAuditTest.java','allGraphsUseSharedWindowsYearAxis()',r'''    @Test public void allGraphsUseSharedWindowsYearAxis() throws Exception {
        String chart=read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R26ChartView.java"); assertTrue(chart.contains("R47GraphGeometry.ticks")); assertTrue(chart.contains("dateLabelRotationDegrees()"));
    }''')
replace_method('R46WindowsGraphSyncPageAuditTest.java','decryptIsTrueStreamingAndProgressive()',r'''    @Test public void decryptIsTrueStreamingAndProgressive() throws Exception {
        String d=read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R46Dsl5Decryptor.java"); assertTrue(d.contains("cipher.update(buffer, 0, n)")); assertTrue(d.contains("cipher.doFinal()"));
        String c=read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R12CloudManager.java"); assertTrue(c.contains("R46Dsl5Decryptor.decrypt")); assertTrue(c.contains("R47RcloneTransfer.download"));
    }''')
replace_method('R46WindowsGraphSyncPageAuditTest.java','versionIsR47()',r'''    @Test public void versionIsR47() throws Exception {
        String g=read("build.gradle"); assertTrue(g.contains("versionCode 47")); assertTrue(g.contains("1.0.0-android-r47-sync-crash-graph-layout-test"));
    }''')

p=TEST/'R45YearAxisProgressiveBackupTest.java'
if p.exists():
    s=p.read_text(encoding='utf-8').replace('assertTrue(axis.contains("R46GraphMath.windowsYearTicks(first, last)"));','assertTrue(axis.contains("R47GraphGeometry.ticks"));'); p.write_text(s,encoding='utf-8')

for p in TEST.glob('R*Test.java'):
    s=p.read_text(encoding='utf-8'); s=s.replace('1.0.0-android-r46-windows-graph-sync-page-audit-test',R47_NAME)
    s=re.sub(r'versionCode\\s*\\(?:=\\s*\\?\\)\\?46',r'versionCode\\s*(?:=\\s*)?47',s); s=s.replace('versionCode 46','versionCode 47').replace('versionIsR46','versionIsR47')
    p.write_text(s,encoding='utf-8')

print('R47 final regression compatibility and runtime guard applied')
