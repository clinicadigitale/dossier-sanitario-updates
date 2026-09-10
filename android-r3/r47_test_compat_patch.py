from pathlib import Path
import re

BASE = Path('android-r3/app/src/main/java/it/dossiersanitario/clinicadigitale/beta')
TEST = Path('android-r3/app/src/test/java/it/dossiersanitario/clinicadigitale/beta')
R47_NAME = '1.0.0-android-r47-sync-crash-graph-layout-test'

# Compile/runtime guard: point hit testing must use exactly the same full-year
# geometry as drawing, and rclone output must never block the caller forever.
chart_path = BASE / 'R26ChartView.java'
chart = chart_path.read_text(encoding='utf-8')
touch_pos = chart.find('    @Override public boolean onTouchEvent(android.view.MotionEvent event) {')
if touch_pos < 0:
    raise SystemExit('R47 compat failed: touch handler missing')
touch = chart[touch_pos:]
old_touch = '        boolean dated = tMin != Long.MAX_VALUE && tMax > tMin;\n\n        int nearest = -1;'
new_touch = '        boolean dated = tMin != Long.MAX_VALUE && tMax >= tMin;\n        long axisMin = dated ? R47GraphGeometry.yearStart(tMin) : tMin;\n        long axisMax = dated ? R47GraphGeometry.yearEndExclusive(tMax) : tMax;\n        if (dated && axisMax <= axisMin) axisMax = axisMin + 1L;\n\n        int nearest = -1;'
if old_touch not in touch:
    raise SystemExit('R47 compat failed: touch time geometry insertion point missing')
touch = touch.replace(old_touch, new_touch, 1)
chart = chart[:touch_pos] + touch
chart_path.write_text(chart, encoding='utf-8')

# Rewrite the transfer helper so timeout runs concurrently with output reading.
# Only the last 30 output lines are retained, keeping memory bounded.
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
        int[] last = new int[]{-1};
        Thread reader = new Thread(() -> {
            try (BufferedReader br = new BufferedReader(new InputStreamReader(process.getInputStream(), StandardCharsets.UTF_8))) {
                String line;
                while ((line = br.readLine()) != null) {
                    synchronized (tail) {
                        if (tail.size() >= 30) tail.removeFirst();
                        tail.addLast(line);
                    }
                    Matcher m = PERCENT.matcher(line);
                    int seen = -1;
                    while (m.find()) seen = Integer.parseInt(m.group(1));
                    if (seen >= 0) {
                        seen = Math.max(0, Math.min(100, seen));
                        if (seen > last[0]) {
                            last[0] = seen;
                            if (progress != null) progress.onPercent(seen);
                        }
                    }
                }
            } catch (Exception ignored) {}
        }, "clinica-r47-rclone-output");
        reader.start();

        boolean finished;
        try {
            finished = process.waitFor(2, TimeUnit.MINUTES);
        } catch (InterruptedException interrupted) {
            process.destroyForcibly();
            Thread.currentThread().interrupt();
            throw new Exception("Sincronizzazione interrotta.");
        }
        if (!finished) {
            process.destroyForcibly();
            try { reader.join(2000L); } catch (InterruptedException ignored) { Thread.currentThread().interrupt(); }
            throw new Exception("Download cloud fermo oltre il tempo massimo.");
        }
        try { reader.join(2000L); } catch (InterruptedException ignored) { Thread.currentThread().interrupt(); }

        if (process.exitValue() != 0) {
            StringBuilder message = new StringBuilder();
            synchronized (tail) {
                for (String line : tail) message.append(line).append('\n');
            }
            String text = message.toString().trim();
            if (text.length() > 900) text = text.substring(text.length() - 900);
            throw new Exception(text.isEmpty() ? "Download cloud non riuscito." : text);
        }
        if (!local.isFile() || local.length() <= 0L) throw new Exception("Download cloud non completato.");
        if (progress != null) progress.onPercent(100);
    }
}
''', encoding='utf-8')


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

for p in TEST.glob('R*Test.java'):
    s = p.read_text(encoding='utf-8')
    s = s.replace('1.0.0-android-r46-windows-graph-sync-page-audit-test', R47_NAME)
    s = re.sub(r'versionCode\\s*\\(?:=\\s*\\?\\)\\?46', r'versionCode\\s*(?:=\\s*)?47', s)
    s = s.replace('versionCode 46', 'versionCode 47')
    s = s.replace('versionCode\\s*(?:=\\s*)?46', 'versionCode\\s*(?:=\\s*)?47')
    s = s.replace('versionIsR46', 'versionIsR47')
    p.write_text(s, encoding='utf-8')

print('R47 predecessor regression compatibility and runtime guard applied')
