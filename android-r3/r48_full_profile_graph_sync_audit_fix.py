from pathlib import Path
import re

BASE = Path('android-r3/app/src/main/java/it/dossiersanitario/clinicadigitale/beta')
TEST = Path('android-r3/app/src/test/java/it/dossiersanitario/clinicadigitale/beta')
MAIN = BASE / 'R6MainActivity.java'
CHART = BASE / 'R26ChartView.java'
CLOUD = BASE / 'R12CloudManager.java'
EXACT = BASE / 'R27ExactWindows.java'
SERIES = BASE / 'R40ClinicalSeries.java'
GRADLE = Path('android-r3/app/build.gradle')


def replace_block(text, signature, replacement, label):
    start = text.find(signature)
    if start < 0:
        raise SystemExit('R48 missing ' + label)
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
    if end < 0: raise SystemExit('R48 unclosed ' + label)
    return text[:start] + replacement.rstrip() + '\n' + text[end:]

# 1) Keep the approved 30/70 landscape unchanged. Fix the shared graph renderer only.
chart = CHART.read_text(encoding='utf-8')
chart = chart.replace('setMinimumHeight(dp(360));', 'setMinimumHeight(dp(400));')

on_draw = r'''    @Override protected void onDraw(Canvas canvas) {
        super.onDraw(canvas);
        boolean hasReference = Double.isFinite(referenceLow) && Double.isFinite(referenceHigh);
        float left = dp(66), right = getWidth() - dp(12), top = dp(24);
        float bottom = getHeight() - dp(hasReference ? 122 : 98);
        if (right <= left || bottom <= top) return;
        if (values.isEmpty()) {
            canvas.drawText(emptyText, left, top + dp(28), label);
            return;
        }

        double[] bounds = scaledBoundsWithReference(dataMin, dataMax, referenceLow, referenceHigh);
        double min = bounds[0], max = bounds[1];

        Paint.Align oldAlign = label.getTextAlign();
        label.setTextAlign(Paint.Align.RIGHT);
        for (int i = 0; i <= 4; i++) {
            float y = top + (bottom - top) * i / 4f;
            canvas.drawLine(left, y, right, y, grid);
            double tick = max - (max - min) * i / 4.0;
            canvas.drawText(shortNumber(tick), left - dp(6), y + dp(4), label);
        }
        label.setTextAlign(oldAlign);

        if (hasReference) {
            drawReferenceLine(canvas, referenceLow, min, max, left, right, top, bottom);
            if (Math.abs(referenceHigh - referenceLow) > 0.000001) drawReferenceLine(canvas, referenceHigh, min, max, left, right, top, bottom);
        }

        long[] times = dateTimes(dates);
        long tMin = Long.MAX_VALUE, tMax = Long.MIN_VALUE;
        for (long t : times) if (t > 0L) { tMin = Math.min(tMin, t); tMax = Math.max(tMax, t); }
        boolean dated = tMin != Long.MAX_VALUE && tMax >= tMin;
        long axisMin = dated ? R47GraphGeometry.yearStart(tMin) : tMin;
        long axisMax = dated ? R47GraphGeometry.yearEndExclusive(tMax) : tMax;
        if (dated && axisMax <= axisMin) axisMax = axisMin + 1L;

        Path p = new Path();
        int[] chronological = R46GraphMath.chronologicalOrder(times, values.size());
        for (int position = 0; position < chronological.length; position++) {
            int i = chronological[position];
            float x;
            if (values.size() == 1) x = (left + right) / 2f;
            else if (dated && i < times.length && times[i] > 0L) x = pointXForTime(times[i], axisMin, axisMax, left, right);
            else x = pointXForIndex(position, values.size(), left, right);
            float y = bottom - (float)((values.get(i) - min) / (max - min)) * (bottom - top);
            if (position == 0) p.moveTo(x, y); else p.lineTo(x, y);
            canvas.drawCircle(x, y, dp(4.0f), point);
        }
        if (values.size() > 1) canvas.drawPath(p, line);

        drawYearAxis(canvas, axisMin, axisMax, left, right, bottom);

        String unit = referenceUnit;
        if (unit == null || unit.isEmpty()) unit = seriesUnit;
        if (unit != null && !unit.isEmpty()) {
            canvas.save();
            canvas.rotate(-90f, dp(30), (top + bottom) / 2f);
            label.setTextAlign(Paint.Align.CENTER);
            canvas.drawText(unit, dp(30), (top + bottom) / 2f, label);
            label.setTextAlign(Paint.Align.LEFT);
            canvas.restore();
        }

        String footer = values.size() + " rilevazioni · min " + shortNumber(dataMin) + " · max " + shortNumber(dataMax);
        canvas.drawText(footer, left, dp(18), label);

        String axisTitle = "Data clinica";
        float aw = label.measureText(axisTitle);
        canvas.drawText(axisTitle, Math.max(left, (getWidth() - aw) / 2f), bottom + dp(54), label);

        if (hasReference) {
            float legendY = getHeight() - dp(18);
            canvas.drawLine(left, legendY - dp(4), left + dp(28), legendY - dp(4), reference);
            String interval = "Intervallo " + shortNumber(referenceLow) + " - " + shortNumber(referenceHigh) + (unit == null || unit.isEmpty() ? "" : " " + unit);
            canvas.drawText(interval, left + dp(38), legendY, label);
            if (referenceDate != null && !referenceDate.isEmpty()) {
                canvas.drawText("Riferimento dal referto del " + shortClinicalDate(referenceDate), left, legendY - dp(24), label);
            }
        }
    }'''
chart = replace_block(chart, '    @Override protected void onDraw(Canvas canvas) {', on_draw, 'chart onDraw')

axis = r'''    private void drawYearAxis(Canvas canvas, long axisMin, long axisMax, float left, float right, float bottom) {
        if (axisMin <= 0L || axisMax <= axisMin) return;
        int firstYear = R47GraphGeometry.yearOf(axisMin);
        int lastYear = R47GraphGeometry.yearOf(axisMax - 1L);
        int[] years = R46GraphMath.windowsYearTicks(firstYear, lastYear);
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
chart = replace_block(chart, '    private void drawYearAxis(', axis, 'year axis')
CHART.write_text(chart, encoding='utf-8')

# 2) Profile/data parity. Freeze the active profile for each scan and remove the Android-only median heuristic.
exact = EXACT.read_text(encoding='utf-8')
marker = '    static JSONArray documents(SharedPreferences prefs) { return data(prefs, "documents"); }\n'
if marker not in exact: raise SystemExit('R48 missing documents accessor')
extra = marker + '''    static JSONArray documentsForProfile(SharedPreferences prefs, String profileId) {\n        if (prefs == null || profileId == null || profileId.trim().isEmpty()) return new JSONArray();\n        return readArrayPref(prefs, key(profileId.trim(), "documents"));\n    }\n'''
exact = exact.replace(marker, extra, 1)
EXACT.write_text(exact, encoding='utf-8')

series = SERIES.read_text(encoding='utf-8')
series = series.replace('JSONArray docs = R27ExactWindows.documents(prefs);', 'String profileId = R27ExactWindows.activeProfileId(prefs);\n        JSONArray docs = R27ExactWindows.documentsForProfile(prefs, profileId);')
series = series.replace('        rows = removeObviousParserExplosions(rows);\n', '')
SERIES.write_text(series, encoding='utf-8')

# 3) Sync crash: restore the proven bounded-memory Bouncy Castle GCM stream.
cloud = CLOUD.read_text(encoding='utf-8')
if 'R46Dsl5Decryptor.decrypt(encryptedPart, plainZip, recovery,' not in cloud:
    raise SystemExit('R48 missing R46 decrypt call')
cloud = cloud.replace('R46Dsl5Decryptor.decrypt(encryptedPart, plainZip, recovery,', 'R22StreamingDsl5.decryptVerified(encryptedPart, plainZip, recovery,', 1)
needle = '            if (progress != null) progress.update(76, "Decifratura completata. Importazione dati Windows...");'
if needle not in cloud: raise SystemExit('R48 missing decrypt completion')
cloud = cloud.replace(needle, '            if (encryptedPart.exists()) encryptedPart.delete();\n' + needle, 1)
cloud = cloud.replace('            } catch (Exception ex) {\n                final String message = r43SyncMessage(ex);', '            } catch (Throwable ex) {\n                final Exception safe = ex instanceof Exception ? (Exception) ex : new Exception(ex.getClass().getSimpleName() + ": " + String.valueOf(ex.getMessage()));\n                final String message = r43SyncMessage(safe);', 1)
CLOUD.write_text(cloud, encoding='utf-8')

# Version.
g = GRADLE.read_text(encoding='utf-8')
g = re.sub(r'versionCode\s*(?:=\s*)?\d+', 'versionCode 48', g, count=1)
g = re.sub(r'versionName\s*(?:=\s*)?[\"\'][^\"\']+[\"\']', 'versionName "1.0.0-android-r48-full-profile-graph-sync-audit-test"', g, count=1)
GRADLE.write_text(g, encoding='utf-8')

# Tests: all shared graphs, Windows year scheme, vertical geometry, profile isolation, no Android value deletion, bounded decrypt.
TEST.mkdir(parents=True, exist_ok=True)
(TEST / 'R48FullProfileGraphSyncAuditTest.java').write_text(r'''package it.dossiersanitario.clinicadigitale.beta;

import static org.junit.Assert.*;
import org.junit.Test;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;

public class R48FullProfileGraphSyncAuditTest {
    private String read(String path) throws Exception { return new String(Files.readAllBytes(Paths.get(path)), StandardCharsets.UTF_8); }

    @Test public void windowsYearSchemeIsIdenticalForReferenceRange() {
        assertArrayEquals(new int[]{2003,2005,2007,2009,2011,2013,2015,2017,2019,2021,2023,2025,2026}, R46GraphMath.windowsYearTicks(2003, 2026));
    }

    @Test public void sharedRendererUsesFullHeightAndSeparatedFooter() throws Exception {
        String c=read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R26ChartView.java");
        assertTrue(c.contains("setMinimumHeight(dp(400))"));
        assertTrue(c.contains("hasReference ? 122 : 98"));
        assertTrue(c.contains("bottom + dp(54)"));
        assertTrue(c.contains("legendY - dp(24)"));
        assertTrue(c.contains("dp(30)"));
    }

    @Test public void everyGraphUsesWindowsYearTicksNotDeviceThinning() throws Exception {
        String c=read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R26ChartView.java");
        assertTrue(c.contains("R46GraphMath.windowsYearTicks(firstYear, lastYear)"));
        assertFalse(c.contains("R47GraphGeometry.ticks(firstYear, lastYear"));
    }

    @Test public void labSeriesIsExplicitlyProfileScoped() throws Exception {
        String e=read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R27ExactWindows.java");
        String s=read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R40ClinicalSeries.java");
        assertTrue(e.contains("documentsForProfile"));
        assertTrue(s.contains("R27ExactWindows.activeProfileId(prefs)"));
        assertTrue(s.contains("R27ExactWindows.documentsForProfile(prefs, profileId)"));
    }

    @Test public void androidDoesNotDeleteWindowsClinicalPointsByMedian() throws Exception {
        String s=read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R40ClinicalSeries.java");
        String method=s.substring(s.indexOf("static JSONArray labSeries"), s.indexOf("static double canonicalValue"));
        assertFalse(method.contains("removeObviousParserExplosions"));
    }

    @Test public void syncUsesBoundedMemoryAuthenticatedDecrypt() throws Exception {
        String c=read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R12CloudManager.java");
        assertTrue(c.contains("R22StreamingDsl5.decryptVerified(encryptedPart, plainZip, recovery"));
        assertFalse(c.contains("R46Dsl5Decryptor.decrypt(encryptedPart, plainZip, recovery"));
        assertTrue(c.contains("if (encryptedPart.exists()) encryptedPart.delete()"));
    }
}
''', encoding='utf-8')

print('R48 full-profile graph and bounded sync audit fix applied')
