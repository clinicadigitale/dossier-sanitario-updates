package it.dossiersanitario.clinicadigitale.beta;

import static org.junit.Assert.*;

import org.junit.Test;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;

public class R45YearAxisProgressiveBackupTest {
    private String read(String path) throws Exception {
        return new String(Files.readAllBytes(Paths.get(path)), StandardCharsets.UTF_8);
    }

    @Test public void yearAxisContainsEveryCalendarYearInChronologicalOrder() {
        long a = R26ChartView.yearStartMillis(2010);
        long b = R26ChartView.yearStartMillis(2013) + 86400000L;
        int[] years = R26ChartView.yearTicks(a, b);
        assertArrayEquals(new int[]{2010, 2011, 2012, 2013}, years);
        assertTrue(R26ChartView.pointXForTime(R26ChartView.yearStartMillis(2011), a, b, 100f, 900f) <
                R26ChartView.pointXForTime(R26ChartView.yearStartMillis(2012), a, b, 100f, 900f));
    }

    @Test public void axisDrawsYearsNotReportDates() throws Exception {
        String chart = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R26ChartView.java");
        int start = chart.indexOf("private void drawYearAxis");
        int end = chart.indexOf("static float pointXForTime", start);
        assertTrue(start >= 0 && end > start);
        String axis = chart.substring(start, end);
        assertTrue(axis.contains("yearTicks(tMin, tMax)"));
        assertTrue(axis.contains("String.valueOf(year)"));
        assertFalse(axis.contains("shortClinicalDate(dates.get(i))"));
        assertFalse(axis.contains("maximumLabels"));
    }

    @Test public void reportPointsKeepDocumentReferenceAndAreInspectable() throws Exception {
        String series = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R40ClinicalSeries.java");
        assertTrue(series.contains("sourceDocumentId"));
        assertTrue(series.contains("sourceDocumentLabel"));
        String chart = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R26ChartView.java");
        assertTrue(chart.contains("pointRecords"));
        assertTrue(chart.contains("onTouchEvent(android.view.MotionEvent event)"));
        assertTrue(chart.contains("sourceDocumentLabel"));
        assertTrue(chart.contains("shortClinicalDate(dates.get(nearest))"));
    }

    @Test public void progressMathAdvancesOnePercentAtATimeWhenBytesAdvance() {
        assertEquals(42, R45ProgressMath.percent(0, 100, 42, 59));
        assertEquals(43, R45ProgressMath.percent(6, 100, 42, 59));
        assertEquals(50, R45ProgressMath.percent(50, 100, 42, 59));
        assertEquals(59, R45ProgressMath.percent(100, 100, 42, 59));
        int previous = 42;
        boolean sawIncrementOfOne = false;
        for (int done = 0; done <= 1000; done++) {
            int now = R45ProgressMath.percent(done, 1000, 42, 59);
            if (now - previous == 1) sawIncrementOfOne = true;
            assertTrue(now >= previous);
            previous = now;
        }
        assertTrue(sawIncrementOfOne);
    }

    @Test public void decryptProgressCountsEncryptedBytesNotOnlyProducedPlaintext() throws Exception {
        String crypto = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R12Crypto.java");
        assertTrue(crypto.contains("class ProgressInputStream"));
        assertTrue(crypto.contains("progress.onBytes(read, total)"));
        assertTrue(crypto.contains("openDsl5File(File file, byte[] keyRaw, Dsl5ReadProgress progress)"));
        String cloud = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R12CloudManager.java");
        assertTrue(cloud.contains("r45RefreshLatestCommittedSnapshot"));
        assertTrue(cloud.contains("R45ProgressMath.percent(read, total, 42, 59)"));
        assertTrue(cloud.contains("R45ProgressMath.percent(encryptedPart.length(), latest.size, 20, 40)"));
        assertTrue(cloud.contains("R45ProgressMath.importPercent(done, total)"));
    }

    @Test public void landscapeThirtySeventyRemainsFrozen() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        assertTrue(main.contains("0.30f"));
        assertTrue(main.contains("0.70f"));
        assertTrue(main.contains("onConfigurationChanged(Configuration newConfig)"));
    }

    @Test public void versionIsR45() throws Exception {
        String gradle = read("build.gradle");
        assertTrue(gradle.matches("(?s).*versionCode\\s*(?:=\\s*)?45.*"));
        assertTrue(gradle.contains("1.0.0-android-r45-year-axis-progressive-backup-test"));
    }
}
