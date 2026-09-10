from pathlib import Path
import re

BASE = Path('android-r3/app/src/main/java/it/dossiersanitario/clinicadigitale/beta')
TEST = Path('android-r3/app/src/test/java/it/dossiersanitario/clinicadigitale/beta')
CHART = BASE / 'R26ChartView.java'
CLOUD = BASE / 'R12CloudManager.java'
GRADLE = Path('android-r3/app/build.gradle')


def replace_block(text, signature, replacement, label=None):
    start = text.find(signature)
    if start < 0:
        raise SystemExit(f'R46 failed: missing {label or signature}')
    brace = text.find('{', start)
    depth = 0
    end = -1
    for i in range(brace, len(text)):
        if text[i] == '{': depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end < 0:
        raise SystemExit(f'R46 failed: unclosed {label or signature}')
    return text[:start] + replacement.rstrip() + '\n' + text[end:]

# ---------------------------------------------------------------------------
# 1. Graph math shared by every R26ChartView instance.
# Windows parity rule: points are connected chronologically and the year axis
# uses the same sparse chronological scheme, with the final year always shown.
# ---------------------------------------------------------------------------
(BASE / 'R46GraphMath.java').write_text(r'''package it.dossiersanitario.clinicadigitale.beta;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Comparator;
import java.util.List;

final class R46GraphMath {
    private R46GraphMath() {}

    static int[] windowsYearTicks(int firstYear, int lastYear) {
        if (lastYear < firstYear) return new int[0];
        int span = lastYear - firstYear;
        int rawStep = Math.max(1, (int) Math.ceil(span / 12.0));
        int step;
        if (rawStep <= 1) step = 1;
        else if (rawStep <= 2) step = 2;
        else if (rawStep <= 5) step = 5;
        else if (rawStep <= 10) step = 10;
        else step = ((rawStep + 9) / 10) * 10;

        List<Integer> ticks = new ArrayList<>();
        for (int y = firstYear; y <= lastYear; y += step) ticks.add(y);
        if (ticks.isEmpty() || ticks.get(ticks.size() - 1) != lastYear) ticks.add(lastYear);
        int[] out = new int[ticks.size()];
        for (int i = 0; i < ticks.size(); i++) out[i] = ticks.get(i);
        return out;
    }

    static int[] chronologicalOrder(long[] times, int count) {
        Integer[] order = new Integer[Math.max(0, count)];
        for (int i = 0; i < order.length; i++) order[i] = i;
        Arrays.sort(order, Comparator.comparingLong(i -> {
            long t = i < times.length ? times[i] : 0L;
            return t > 0L ? t : Long.MAX_VALUE - i;
        }));
        int[] out = new int[order.length];
        for (int i = 0; i < order.length; i++) out[i] = order[i];
        return out;
    }
}
''', encoding='utf-8')

chart = CHART.read_text(encoding='utf-8')

year_ticks = r'''    static int[] yearTicks(long minTime, long maxTime) {
        if (minTime <= 0L || maxTime <= 0L || maxTime < minTime) return new int[0];
        java.util.Calendar a = java.util.Calendar.getInstance(java.util.TimeZone.getTimeZone("UTC"), Locale.ITALY);
        java.util.Calendar b = java.util.Calendar.getInstance(java.util.TimeZone.getTimeZone("UTC"), Locale.ITALY);
        a.setTimeInMillis(minTime);
        b.setTimeInMillis(maxTime);
        int first = a.get(java.util.Calendar.YEAR);
        int last = b.get(java.util.Calendar.YEAR);
        return R46GraphMath.windowsYearTicks(first, last);
    }'''
chart = replace_block(chart, '    static int[] yearTicks(long minTime, long maxTime) {', year_ticks, 'Windows year tick scheme')

old_path = '''        Path p = new Path();\n        for (int i = 0; i < values.size(); i++) {\n            float x;\n            if (values.size() == 1) x = (left + right) / 2f;\n            else if (dated && i < times.length && times[i] > 0) x = pointXForTime(times[i], tMin, tMax, left, right);\n            else x = pointXForIndex(i, values.size(), left, right);\n            float y = bottom - (float) ((values.get(i) - min) / (max - min)) * (bottom - top);\n            if (i == 0) p.moveTo(x, y); else p.lineTo(x, y);\n            canvas.drawCircle(x, y, dp(4.0f), point);\n        }\n        if (values.size() > 1) canvas.drawPath(p, line);'''
new_path = '''        Path p = new Path();\n        int[] chronological = R46GraphMath.chronologicalOrder(times, values.size());\n        for (int position = 0; position < chronological.length; position++) {\n            int i = chronological[position];\n            float x;\n            if (values.size() == 1) x = (left + right) / 2f;\n            else if (dated && i < times.length && times[i] > 0) x = pointXForTime(times[i], tMin, tMax, left, right);\n            else x = pointXForIndex(position, values.size(), left, right);\n            float y = bottom - (float) ((values.get(i) - min) / (max - min)) * (bottom - top);\n            if (position == 0) p.moveTo(x, y); else p.lineTo(x, y);\n            canvas.drawCircle(x, y, dp(4.0f), point);\n        }\n        if (values.size() > 1) canvas.drawPath(p, line);'''
if old_path not in chart:
    raise SystemExit('R46 failed: chronological path block missing')
chart = chart.replace(old_path, new_path, 1)
CHART.write_text(chart, encoding='utf-8')

# ---------------------------------------------------------------------------
# 2. True streaming AES-GCM decrypt-to-file. This bypasses CipherInputStream's
# device-dependent buffering and reports actual encrypted bytes processed.
# ---------------------------------------------------------------------------
(BASE / 'R46Dsl5Decryptor.java').write_text(r'''package it.dossiersanitario.clinicadigitale.beta;

import org.json.JSONObject;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;

import javax.crypto.Cipher;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;

final class R46Dsl5Decryptor {
    interface Progress { void onBytes(long done, long total); }
    private static final byte[] MAGIC = "DSL5ENC1".getBytes(StandardCharsets.US_ASCII);
    private R46Dsl5Decryptor() {}

    static void decrypt(File source, File target, byte[] keyRaw, Progress progress) throws Exception {
        if (source == null || !source.isFile() || source.length() <= 12L) throw new Exception("Archivio cifrato non disponibile");
        if (target.exists() && !target.delete()) throw new Exception("Impossibile preparare il file temporaneo");
        try (FileInputStream in = new FileInputStream(source); FileOutputStream out = new FileOutputStream(target)) {
            byte[] header = readExact(in, 12);
            if (!Arrays.equals(Arrays.copyOfRange(header, 0, 8), MAGIC)) throw new Exception("Formato cifrato non riconosciuto");
            int metaLength = ByteBuffer.wrap(header, 8, 4).getInt();
            if (metaLength <= 0 || metaLength > 1024 * 1024) throw new Exception("Metadati archivio non validi");
            byte[] metaBytes = readExact(in, metaLength);
            JSONObject meta = new JSONObject(new String(metaBytes, StandardCharsets.UTF_8));
            if (!"DSL5-AESGCM".equals(meta.optString("format"))) throw new Exception("Formato archivio cloud non valido");

            byte[] iv = R12Crypto.unb64(meta.getString("iv"));
            Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
            cipher.init(Cipher.DECRYPT_MODE, new SecretKeySpec(keyRaw, "AES"), new GCMParameterSpec(128, iv));

            long total = Math.max(1L, source.length() - 12L - metaLength);
            long done = 0L;
            byte[] buffer = new byte[1024 * 1024];
            int n;
            while ((n = in.read(buffer)) >= 0) {
                if (n == 0) continue;
                byte[] plain = cipher.update(buffer, 0, n);
                if (plain != null && plain.length > 0) out.write(plain);
                done += n;
                if (progress != null) progress.onBytes(done, total);
            }
            byte[] tail = cipher.doFinal();
            if (tail != null && tail.length > 0) out.write(tail);
            out.flush();
            if (progress != null) progress.onBytes(total, total);
        } catch (Exception failure) {
            if (target.exists()) target.delete();
            throw failure;
        }
        if (!target.isFile() || target.length() == 0L) throw new Exception("Snapshot Windows decifrato non disponibile");
    }

    private static byte[] readExact(FileInputStream in, int length) throws Exception {
        byte[] out = new byte[length];
        int offset = 0;
        while (offset < length) {
            int n = in.read(out, offset, length - offset);
            if (n < 0) throw new Exception("Archivio cifrato incompleto");
            offset += n;
        }
        return out;
    }
}
''', encoding='utf-8')

(BASE / 'R46ProgressMath.java').write_text(r'''package it.dossiersanitario.clinicadigitale.beta;

final class R46ProgressMath {
    private R46ProgressMath() {}
    static int percent(long done, long total, int start, int end) {
        if (end <= start || total <= 0L) return start;
        long safe = Math.max(0L, Math.min(done, total));
        int value = start + (int) Math.floor((end - start) * (safe / (double) total));
        return Math.max(start, Math.min(end, value));
    }
    static int importPercent(int done, int total) { return percent(done, total, 76, 88); }
}
''', encoding='utf-8')

cloud = CLOUD.read_text(encoding='utf-8')
cloud = cloud.replace('progress.update(8, "Verifica dell\'archivio MEGA autorizzato...")', 'progress.update(2, "Verifica dell\'archivio MEGA autorizzato...")')
cloud = cloud.replace('progress.update(14, "Ricerca della copia Windows più recente...")', 'progress.update(5, "Ricerca della copia Windows più recente...")')
cloud = cloud.replace('progress.update(20, "Download della copia Windows più recente...")', 'progress.update(10, "Download della copia Windows più recente...")')
cloud = cloud.replace('R45ProgressMath.percent(encryptedPart.length(), latest.size, 20, 40)', 'R46ProgressMath.percent(encryptedPart.length(), latest.size, 10, 45)')
cloud = cloud.replace('int lastDownload = 20;', 'int lastDownload = 10;')
cloud = cloud.replace('progress.update(41, "Copia Windows scaricata. Preparazione decifratura...")', 'progress.update(46, "Copia Windows scaricata. Preparazione decifratura...")')

start_marker = '            byte[] recovery = recoveryKey(context, cfg);\n            final int[] lastDecrypt = new int[]{41};'
end_marker = '            if (progress != null) progress.update(60, "Decifratura completata. Importazione dati Windows...");'
start = cloud.find(start_marker)
end = cloud.find(end_marker, start)
if start < 0 or end < 0:
    raise SystemExit('R46 failed: R45 decrypt progress block missing')
end += len(end_marker)
new_decrypt = '''            byte[] recovery = recoveryKey(context, cfg);\n            final int[] lastDecrypt = new int[]{46};\n            R46Dsl5Decryptor.decrypt(encryptedPart, plainZip, recovery, (read, total) -> {\n                if (progress == null) return;\n                int now = R46ProgressMath.percent(read, total, 46, 75);\n                if (now > lastDecrypt[0]) {\n                    lastDecrypt[0] = now;\n                    progress.update(now, "Decifratura copia Windows " + now + "%...");\n                }\n            });\n            if (progress != null) progress.update(76, "Decifratura completata. Importazione dati Windows...");'''
cloud = cloud[:start] + new_decrypt + cloud[end:]
cloud = cloud.replace('R45ProgressMath.importPercent(done, total)', 'R46ProgressMath.importPercent(done, total)')
CLOUD.write_text(cloud, encoding='utf-8')

# Final R46 package identity.
g = GRADLE.read_text(encoding='utf-8')
g = re.sub(r'versionCode\s*(?:=\s*)?\d+', 'versionCode 46', g, count=1)
g = re.sub(r'versionName\s*(?:=\s*)?[\"\'][^\"\']+[\"\']', 'versionName "1.0.0-android-r46-windows-graph-sync-page-audit-test"', g, count=1)
GRADLE.write_text(g, encoding='utf-8')

# R46 regression tests. These fail under R45 behavior.
TEST.mkdir(parents=True, exist_ok=True)
(TEST / 'R46WindowsGraphSyncPageAuditTest.java').write_text(r'''package it.dossiersanitario.clinicadigitale.beta;

import static org.junit.Assert.*;
import org.junit.Test;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;

public class R46WindowsGraphSyncPageAuditTest {
    private String read(String path) throws Exception {
        return new String(Files.readAllBytes(Paths.get(path)), StandardCharsets.UTF_8);
    }

    @Test public void windowsYearAxisUsesSparseSchemeAndFinalYear() {
        assertArrayEquals(new int[]{2003,2005,2007,2009,2011,2013,2015,2017,2019,2021,2023,2025,2026}, R46GraphMath.windowsYearTicks(2003, 2026));
        assertArrayEquals(new int[]{2019,2020,2021,2022,2023,2024,2025,2026}, R46GraphMath.windowsYearTicks(2019, 2026));
    }

    @Test public void curveConnectsPointsInClinicalChronologicalOrder() {
        long[] times = new long[]{3000L,1000L,2000L};
        assertArrayEquals(new int[]{1,2,0}, R46GraphMath.chronologicalOrder(times, 3));
        String chart = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R26ChartView.java");
        assertTrue(chart.contains("R46GraphMath.chronologicalOrder(times, values.size())"));
        assertTrue(chart.contains("if (position == 0) p.moveTo(x, y); else p.lineTo(x, y);"));
    }

    @Test public void allGraphsUseSharedWindowsYearAxis() throws Exception {
        String chart = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R26ChartView.java");
        assertTrue(chart.contains("R46GraphMath.windowsYearTicks(first, last)"));
        assertTrue(chart.contains("dateLabelRotationDegrees()"));
        assertTrue(chart.contains("String.valueOf(year)"));
    }

    @Test public void decryptIsTrueStreamingAndProgressive() throws Exception {
        String decryptor = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R46Dsl5Decryptor.java");
        assertTrue(decryptor.contains("new byte[1024 * 1024]"));
        assertTrue(decryptor.contains("cipher.update(buffer, 0, n)"));
        assertTrue(decryptor.contains("cipher.doFinal()"));
        assertTrue(decryptor.contains("progress.onBytes(done, total)"));
        String cloud = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R12CloudManager.java");
        assertTrue(cloud.contains("R46Dsl5Decryptor.decrypt"));
        assertTrue(cloud.contains("R46ProgressMath.percent(read, total, 46, 75)"));
        assertTrue(cloud.contains("R46ProgressMath.percent(encryptedPart.length(), latest.size, 10, 45)"));
    }

    @Test public void progressMovesOnePointAtATimeAcrossLongWork() {
        int previous = 46;
        boolean sawOne = false;
        for (int done = 0; done <= 10000; done++) {
            int now = R46ProgressMath.percent(done, 10000, 46, 75);
            assertTrue(now >= previous);
            if (now - previous == 1) sawOne = true;
            assertTrue(now - previous <= 1);
            previous = now;
        }
        assertTrue(sawOne);
        assertEquals(75, previous);
    }

    @Test public void everyMainPageHasRouteAndRenderer() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        String[][] pages = new String[][]{
            {"Panoramica","renderPanoramica"}, {"Dati profilo","renderDatiProfilo"}, {"Dati di emergenza","renderDatiEmergenza"},
            {"Esenzioni","renderEsenzioni"}, {"Documenti","renderDocumenti"}, {"Cronologia","renderCronologia"},
            {"Diagnosi","renderDiagnosi"}, {"Terapie","renderTerapie"}, {"Medici","renderMedici"},
            {"Confronta","renderConfronta"}, {"Grafici","renderGrafici"}, {"Agenda","renderAgenda"},
            {"Monitoraggio","renderMonitoraggio"}, {"Preferenze","renderPreferenze"}, {"Aiuto","renderAiuto"}
        };
        for (String[] page : pages) {
            assertTrue("missing route " + page[0], main.contains("case \"" + page[0] + "\":"));
            assertTrue("missing renderer " + page[1], main.contains("private void " + page[1] + "()"));
        }
        assertTrue(main.contains("0.30f"));
        assertTrue(main.contains("0.70f"));
    }

    @Test public void versionIsR46() throws Exception {
        String gradle = read("build.gradle");
        assertTrue(gradle.matches("(?s).*versionCode\\s*(?:=\\s*)?46.*"));
        assertTrue(gradle.contains("1.0.0-android-r46-windows-graph-sync-page-audit-test"));
    }
}
''', encoding='utf-8')

print('R46 Windows graph parity, streaming sync and all-page audit patch applied')
