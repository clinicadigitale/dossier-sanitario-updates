package it.dossiersanitario.clinicadigitale.beta;

import static org.junit.Assert.*;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;

import org.junit.Test;

public class R44RealDeviceParitySyncTest {
    private String read(String path) throws Exception {
        return new String(Files.readAllBytes(Paths.get(path)), StandardCharsets.UTF_8);
    }

    @Test public void landscapeIsExactlyThirtySeventyAndRotationRebuildRemains() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        assertTrue(main.contains("0.30f"));
        assertTrue(main.contains("0.70f"));
        assertFalse(main.contains("R43LayoutGeometry.landscapeLabelWidthPx(getResources().getDisplayMetrics().widthPixels"));
        assertTrue(main.contains("onConfigurationChanged(Configuration newConfig)"));
        assertTrue(main.contains("renderSection(currentSection)"));
    }

    @Test public void graphUsesWindowsTimeProportionalGeometryNotEqualObservationSpacing() throws Exception {
        float left = 100f, right = 900f;
        long day = 24L * 60L * 60L * 1000L;
        float x0 = R26ChartView.pointXForTime(0L, 0L, 10L * day, left, right);
        float x1 = R26ChartView.pointXForTime(1L * day, 0L, 10L * day, left, right);
        float x5 = R26ChartView.pointXForTime(5L * day, 0L, 10L * day, left, right);
        assertEquals(left, x0, 0.001f);
        assertTrue(x1 - x0 < x5 - x1);
        assertEquals(500f, x5, 0.001f);
        assertEquals(-45f, R26ChartView.dateLabelRotationDegrees(), 0.001f);
        String chart = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R26ChartView.java");
        assertTrue(chart.contains("pointXForTime(times[i], tMin, tMax, left, right)"));
    }

    @Test public void valueSelectorParameterDiscoveryIsSinglePass() throws Exception {
        String series = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R40ClinicalSeries.java");
        int start = series.indexOf("static JSONArray availableLabParameters");
        int end = series.indexOf("static JSONArray labSeries", start);
        assertTrue(start >= 0 && end > start);
        String block = series.substring(start, end);
        assertFalse(block.contains("labSeries(prefs"));
        assertTrue(block.contains("R27ExactWindows.documents(prefs)"));
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        assertTrue(main.contains("JSONArray labs = R40ClinicalSeries.availableLabParameters(prefs)"));
    }

    @Test public void syncHasDeterminateMilestonesAndBoundedSnapshotFallback() throws Exception {
        String cloud = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R12CloudManager.java");
        String rclone = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R12Rclone.java");
        assertTrue(cloud.contains("public static void syncInteractiveR44"));
        assertTrue(cloud.contains("dialog.setIndeterminate(false)"));
        assertTrue(cloud.contains("dialog.setMax(100)"));
        assertTrue(cloud.contains("r44RefreshLatestCommittedSnapshot"));
        assertTrue(cloud.contains("latestSnapshotR44"));
        assertTrue(cloud.contains("R12Rclone.lsJsonBounded(context, snapshotsRoot, false, 30L)"));
        assertTrue(cloud.contains("R12Rclone.lsfBounded(context, snapshotsRoot, 30L)"));
        assertTrue(cloud.contains("Download della copia Windows più recente"));
        assertTrue(cloud.contains("Importazione dei dati Windows nel Dossier Android"));
        assertTrue(rclone.contains("public static String lsfBounded"));
        assertTrue(rclone.contains("--format\", \"ps"));
    }

    @Test public void versionIsR44() throws Exception {
        String gradle = read("build.gradle");
        assertTrue(gradle.contains("versionCode 44"));
        assertTrue(gradle.contains("1.0.0-android-r44-realdevice-parity-sync-test"));
    }
}
