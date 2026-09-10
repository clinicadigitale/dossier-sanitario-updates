from pathlib import Path
import re

BASE = Path('android-r3/app/src/main/java/it/dossiersanitario/clinicadigitale/beta')
TEST = Path('android-r3/app/src/test/java/it/dossiersanitario/clinicadigitale/beta')
CHART = BASE / 'R26ChartView.java'
CLOUD = BASE / 'R12CloudManager.java'
GRADLE = Path('android-r3/app/build.gradle')


def require(text, needle, label):
    if needle not in text:
        raise SystemExit('R47 failed: missing ' + label)

# ---------------------------------------------------------------------------
# 1. GRAPH: use complete calendar-year domain so first/last year spacing is
# not compressed by the first/last clinical observation. Keep one shared
# renderer for every graph, choose sparse ticks responsively, reclaim left
# margin, and reserve independent vertical space for axis title and legend.
# ---------------------------------------------------------------------------
(BASE / 'R47GraphGeometry.java').write_text(r'''package it.dossiersanitario.clinicadigitale.beta;

import java.util.ArrayList;
import java.util.Calendar;
import java.util.List;
import java.util.TimeZone;

final class R47GraphGeometry {
    private R47GraphGeometry() {}

    static long yearStart(long time) {
        if (time <= 0L) return 0L;
        Calendar c = Calendar.getInstance(TimeZone.getTimeZone("UTC"));
        c.setTimeInMillis(time);
        int year = c.get(Calendar.YEAR);
        c.clear();
        c.setTimeZone(TimeZone.getTimeZone("UTC"));
        c.set(Calendar.YEAR, year);
        c.set(Calendar.MONTH, Calendar.JANUARY);
        c.set(Calendar.DAY_OF_MONTH, 1);
        return c.getTimeInMillis();
    }

    static long yearEndExclusive(long time) {
        if (time <= 0L) return 0L;
        Calendar c = Calendar.getInstance(TimeZone.getTimeZone("UTC"));
        c.setTimeInMillis(time);
        int year = c.get(Calendar.YEAR) + 1;
        c.clear();
        c.setTimeZone(TimeZone.getTimeZone("UTC"));
        c.set(Calendar.YEAR, year);
        c.set(Calendar.MONTH, Calendar.JANUARY);
        c.set(Calendar.DAY_OF_MONTH, 1);
        return c.getTimeInMillis();
    }

    static int yearOf(long time) {
        Calendar c = Calendar.getInstance(TimeZone.getTimeZone("UTC"));
        c.setTimeInMillis(time);
        return c.get(Calendar.YEAR);
    }

    static int[] ticks(int firstYear, int lastYear, float plotWidthPx, float density) {
        if (lastYear < firstYear) return new int[0];
        float safeDensity = density <= 0f ? 1f : density;
        int maxLabels = Math.max(3, Math.min(13, (int)Math.floor(plotWidthPx / (44f * safeDensity))));
        int span = Math.max(0, lastYear - firstYear);
        int raw = Math.max(1, (int)Math.ceil(span / (double)Math.max(1, maxLabels - 1)));
        int step;
        if (raw <= 1) step = 1;
        else if (raw <= 2) step = 2;
        else if (raw <= 5) step = 5;
        else if (raw <= 10) step = 10;
        else step = ((raw + 9) / 10) * 10;

        List<Integer> list = new ArrayList<>();
        for (int y = firstYear; y <= lastYear; y += step) list.add(y);
        if (list.isEmpty()) list.add(firstYear);
        int lastTick = list.get(list.size() - 1);
        if (lastTick != lastYear) {
            if (list.size() > 1 && lastYear - lastTick < Math.max(1, step / 2)) list.set(list.size() - 1, lastYear);
            else list.add(lastYear);
        }
        int[] out = new int[list.size()];
        for (int i = 0; i < out.length; i++) out[i] = list.get(i);
        return out;
    }
}
''', encoding='utf-8')

chart = CHART.read_text(encoding='utf-8')
require(chart, 'float left = dp(82), right = getWidth() - dp(18), top = dp(38);', 'chart margins')
chart = chart.replace('float left = dp(82), right = getWidth() - dp(18), top = dp(38);',
                      'float left = dp(66), right = getWidth() - dp(12), top = dp(38);')
chart = chart.replace('float bottom = getHeight() - dp(hasReference ? 132 : 108);',
                      'float bottom = getHeight() - dp(hasReference ? 154 : 116);')
chart = chart.replace('left - dp(10)', 'left - dp(6)')
chart = chart.replace('canvas.rotate(-90f, dp(16), (top + bottom) / 2f);',
                      'canvas.rotate(-90f, dp(10), (top + bottom) / 2f);')
chart = chart.replace('canvas.drawText(unit, dp(16), (top + bottom) / 2f, label);',
                      'canvas.drawText(unit, dp(10), (top + bottom) / 2f, label);')
chart = chart.replace('bottom + dp(88)', 'bottom + dp(64)')

# Both point geometry and year-axis geometry use the full calendar-year domain.
old = '''        boolean dated = tMin != Long.MAX_VALUE && tMax > tMin;\n\n        Path p = new Path();'''
new = '''        boolean dated = tMin != Long.MAX_VALUE && tMax >= tMin;\n        long axisMin = dated ? R47GraphGeometry.yearStart(tMin) : tMin;\n        long axisMax = dated ? R47GraphGeometry.yearEndExclusive(tMax) : tMax;\n        if (dated && axisMax <= axisMin) axisMax = axisMin + 1L;\n\n        Path p = new Path();'''
require(chart, old, 'dated/path block')
chart = chart.replace(old, new, 1)
chart = chart.replace('pointXForTime(times[i], tMin, tMax, left, right)',
                      'pointXForTime(times[i], axisMin, axisMax, left, right)')
chart = chart.replace('drawYearAxis(canvas, tMin, tMax, left, right, bottom);',
                      'drawYearAxis(canvas, axisMin, axisMax, left, right, bottom);')

# Replace year-axis implementation with responsive sparse tick spacing. The
# tick anchors remain true calendar positions, but endpoint compression is gone.
sig = '    private void drawYearAxis(Canvas canvas, long tMin, long tMax, float left, float right, float bottom) {'
start = chart.find(sig)
if start < 0: raise SystemExit('R47 failed: year axis method missing')
brace = chart.find('{', start); depth = 0; end = -1
for i in range(brace, len(chart)):
    if chart[i] == '{': depth += 1
    elif chart[i] == '}':
        depth -= 1
        if depth == 0:
            end = i + 1; break
if end < 0: raise SystemExit('R47 failed: year axis method unclosed')
axis = r'''    private void drawYearAxis(Canvas canvas, long axisMin, long axisMax, float left, float right, float bottom) {
        if (axisMin <= 0L || axisMax <= axisMin) return;
        int firstYear = R47GraphGeometry.yearOf(axisMin);
        int lastYear = R47GraphGeometry.yearOf(axisMax - 1L);
        int[] years = R47GraphGeometry.ticks(firstYear, lastYear, right - left, getResources().getDisplayMetrics().density);
        Paint.Align previous = label.getTextAlign();
        label.setTextAlign(Paint.Align.RIGHT);
        for (int year : years) {
            long tickTime = yearStartMillis(year);
            float x = pointXForTime(tickTime, axisMin, axisMax, left, right);
            canvas.drawLine(x, bottom, x, bottom + dp(5), grid);
            canvas.save();
            canvas.rotate(dateLabelRotationDegrees(), x, bottom + dp(20));
            canvas.drawText(String.valueOf(year), x, bottom + dp(20), label);
            canvas.restore();
        }
        label.setTextAlign(previous);
    }'''
chart = chart[:start] + axis + chart[end:]
CHART.write_text(chart, encoding='utf-8')

# ---------------------------------------------------------------------------
# 2. SYNC: eliminate the nested daemon download thread and rclone's default
# memory-heavy transfer settings. Drain rclone output continuously with a
# bounded tail, parse its real transfer percentage, and fail cleanly instead
# of allowing an app-killing runaway process or unbounded output buffer.
# ---------------------------------------------------------------------------
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
        command.add(exe.getAbsolutePath());
        command.add("copyto"); command.add(remote); command.add(local.getAbsolutePath());
        command.add("--config"); command.add(R12Rclone.configFile(context).getAbsolutePath());
        command.add("--transfers"); command.add("1");
        command.add("--checkers"); command.add("1");
        command.add("--buffer-size"); command.add("512K");
        command.add("--multi-thread-streams"); command.add("1");
        command.add("--retries"); command.add("2");
        command.add("--low-level-retries"); command.add("4");
        command.add("--contimeout"); command.add("15s");
        command.add("--timeout"); command.add("60s");
        command.add("--stats"); command.add("1s");
        command.add("--stats-one-line");
        command.add("--log-level"); command.add("NOTICE");

        ProcessBuilder builder = new ProcessBuilder(command);
        builder.redirectErrorStream(true);
        builder.environment().put("TMPDIR", context.getCacheDir().getAbsolutePath());
        builder.environment().put("HOME", context.getFilesDir().getAbsolutePath());
        Process process = builder.start();
        ArrayDeque<String> tail = new ArrayDeque<>();
        int last = -1;
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream(), StandardCharsets.UTF_8))) {
            String line;
            while ((line = reader.readLine()) != null) {
                if (tail.size() >= 30) tail.removeFirst();
                tail.addLast(line);
                Matcher m = PERCENT.matcher(line);
                int seen = -1;
                while (m.find()) seen = Integer.parseInt(m.group(1));
                if (seen >= 0) {
                    seen = Math.max(0, Math.min(100, seen));
                    if (seen > last) {
                        last = seen;
                        if (progress != null) progress.onPercent(seen);
                    }
                }
            }
        }
        boolean finished = process.waitFor(2, TimeUnit.MINUTES);
        if (!finished) {
            process.destroyForcibly();
            throw new Exception("Download cloud fermo oltre il tempo massimo.");
        }
        if (process.exitValue() != 0) {
            StringBuilder message = new StringBuilder();
            for (String line : tail) message.append(line).append('\n');
            String text = message.toString().trim();
            if (text.length() > 900) text = text.substring(text.length() - 900);
            throw new Exception(text.isEmpty() ? "Download cloud non riuscito." : text);
        }
        if (!local.isFile() || local.length() <= 0L) throw new Exception("Download cloud non completato.");
        if (progress != null) progress.onPercent(100);
    }
}
''', encoding='utf-8')

cloud = CLOUD.read_text(encoding='utf-8')
old_download = '''            if (progress != null) progress.update(10, "Download della copia Windows più recente...");\n            java.util.concurrent.atomic.AtomicReference<Throwable> downloadError = new java.util.concurrent.atomic.AtomicReference<>();\n            Thread download = new Thread(() -> {\n                try {\n                    R12Rclone.copyFromRemote(context, cloudRoot(cfg) + "/snapshots/" + latest.name, encryptedPart);\n                } catch (Throwable failure) {\n                    downloadError.set(failure);\n                }\n            }, "clinica-r45-snapshot-download");\n            download.setDaemon(true);\n            download.start();\n            int lastDownload = 10;\n            while (download.isAlive()) {\n                if (latest.size > 0L && progress != null) {\n                    int now = R46ProgressMath.percent(encryptedPart.length(), latest.size, 10, 45);\n                    if (now > lastDownload) {\n                        lastDownload = now;\n                        progress.update(now, "Download copia Windows " + now + "%...");\n                    }\n                }\n                try { download.join(250L); }\n                catch (InterruptedException interrupted) { Thread.currentThread().interrupt(); throw new Exception("Sincronizzazione interrotta."); }\n            }\n            Throwable downloadFailure = downloadError.get();\n            if (downloadFailure != null) throw new Exception(String.valueOf(downloadFailure.getMessage()), downloadFailure);'''
new_download = '''            if (progress != null) progress.update(10, "Download della copia Windows più recente...");\n            final int[] lastDownload = new int[]{10};\n            R47RcloneTransfer.download(context, cloudRoot(cfg) + "/snapshots/" + latest.name, encryptedPart, transferred -> {\n                if (progress == null) return;\n                int now = 10 + (int)Math.floor(35.0 * Math.max(0, Math.min(100, transferred)) / 100.0);\n                if (now > lastDownload[0]) {\n                    lastDownload[0] = now;\n                    progress.update(now, "Download copia Windows " + transferred + "%...");\n                }\n            });'''
require(cloud, old_download, 'R46 nested download block')
cloud = cloud.replace(old_download, new_download, 1)
CLOUD.write_text(cloud, encoding='utf-8')

# Final identity.
g = GRADLE.read_text(encoding='utf-8')
g = re.sub(r'versionCode\s*(?:=\s*)?\d+', 'versionCode 47', g, count=1)
g = re.sub(r'versionName\s*(?:=\s*)?[\"\'][^\"\']+[\"\']', 'versionName "1.0.0-android-r47-sync-crash-graph-layout-test"', g, count=1)
GRADLE.write_text(g, encoding='utf-8')

# New tests that fail under R46.
TEST.mkdir(parents=True, exist_ok=True)
(TEST / 'R47SyncCrashGraphLayoutTest.java').write_text(r'''package it.dossiersanitario.clinicadigitale.beta;

import static org.junit.Assert.*;
import org.junit.Test;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;

public class R47SyncCrashGraphLayoutTest {
    private String read(String path) throws Exception { return new String(Files.readAllBytes(Paths.get(path)), StandardCharsets.UTF_8); }

    @Test public void calendarDomainRemovesCompressedEndpoints() {
        long mid2021 = R26ChartView.yearStartMillis(2021) + 180L * 86400000L;
        long mid2026 = R26ChartView.yearStartMillis(2026) + 180L * 86400000L;
        long start = R47GraphGeometry.yearStart(mid2021);
        long end = R47GraphGeometry.yearEndExclusive(mid2026);
        assertEquals(R26ChartView.yearStartMillis(2021), start);
        assertEquals(R26ChartView.yearStartMillis(2027), end);
        float x21 = R26ChartView.pointXForTime(R26ChartView.yearStartMillis(2021), start, end, 0f, 600f);
        float x22 = R26ChartView.pointXForTime(R26ChartView.yearStartMillis(2022), start, end, 0f, 600f);
        float x25 = R26ChartView.pointXForTime(R26ChartView.yearStartMillis(2025), start, end, 0f, 600f);
        float x26 = R26ChartView.pointXForTime(R26ChartView.yearStartMillis(2026), start, end, 0f, 600f);
        assertEquals(x22 - x21, x26 - x25, 1.0f);
    }

    @Test public void narrowAndroidPlotUsesResponsiveSparseYears() {
        int[] years = R47GraphGeometry.ticks(2003, 2026, 280f, 1f);
        assertTrue(years.length <= 7);
        assertEquals(2003, years[0]);
        assertEquals(2026, years[years.length - 1]);
        for (int i=1;i<years.length;i++) assertTrue(years[i] > years[i-1]);
    }

    @Test public void graphReservesSeparateAxisAndLegendSpace() throws Exception {
        String chart = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R26ChartView.java");
        assertTrue(chart.contains("hasReference ? 154 : 116"));
        assertTrue(chart.contains("bottom + dp(64)"));
        assertTrue(chart.contains("float left = dp(66)"));
        assertTrue(chart.contains("dp(10), (top + bottom) / 2f"));
    }

    @Test public void syncDownloadIsSingleProcessLowMemoryAndBounded() throws Exception {
        String transfer = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R47RcloneTransfer.java");
        assertTrue(transfer.contains("--buffer-size"));
        assertTrue(transfer.contains("512K"));
        assertTrue(transfer.contains("--multi-thread-streams"));
        assertTrue(transfer.contains("--stats-one-line"));
        assertTrue(transfer.contains("ArrayDeque<String> tail"));
        assertTrue(transfer.contains("process.waitFor(2, TimeUnit.MINUTES)"));
        String cloud = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R12CloudManager.java");
        assertTrue(cloud.contains("R47RcloneTransfer.download"));
        assertFalse(cloud.contains("download.setDaemon(true)"));
    }
}
''', encoding='utf-8')

print('R47 sync crash and graph layout fix applied')
