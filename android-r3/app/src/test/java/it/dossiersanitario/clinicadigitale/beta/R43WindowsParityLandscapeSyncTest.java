package it.dossiersanitario.clinicadigitale.beta;

import static org.junit.Assert.*;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;

import org.junit.Test;

public class R43WindowsParityLandscapeSyncTest {
    @Test public void landscapeUsesRealPixelWidthAndKeepsPortraitFrozen() {
        float density = 2.0f;
        assertEquals(184, R43LayoutGeometry.portraitLabelWidthPx(density));
        int landscape = R43LayoutGeometry.landscapeLabelWidthPx(1600, density);
        assertEquals(768, landscape);
        assertTrue(landscape > R43LayoutGeometry.portraitLabelWidthPx(density) * 3);
    }

    @Test public void chartUsesEvenWindowsLikeObservationSpacing() {
        float left = 82f, right = 918f;
        float x0 = R26ChartView.pointXForIndex(0, 5, left, right);
        float x1 = R26ChartView.pointXForIndex(1, 5, left, right);
        float x2 = R26ChartView.pointXForIndex(2, 5, left, right);
        float x4 = R26ChartView.pointXForIndex(4, 5, left, right);
        assertEquals(left, x0, 0.001f);
        assertEquals(right, x4, 0.001f);
        assertEquals(x1 - x0, x2 - x1, 0.001f);
        assertEquals(-45f, R26ChartView.dateLabelRotationDegrees(), 0.001f);
    }

    @Test public void syncLookupIsBoundedAndDoesNotSilentlyAcceptStaleSnapshot() throws Exception {
        Path root = Paths.get(System.getProperty("user.dir"));
        if (root.endsWith("app")) root = root.getParent();
        Path cloud = root.resolve("app/src/main/java/it/dossiersanitario/clinicadigitale/beta/R12CloudManager.java");
        Path rclone = root.resolve("app/src/main/java/it/dossiersanitario/clinicadigitale/beta/R12Rclone.java");
        String c = new String(Files.readAllBytes(cloud), StandardCharsets.UTF_8);
        String r = new String(Files.readAllBytes(rclone), StandardCharsets.UTF_8);
        assertTrue(c.contains("verifyArchiveManifestR43"));
        assertTrue(c.contains("lsJsonBounded(context, snapshotsRoot, false, 60L)"));
        assertTrue(c.contains("Nessuna copia Windows committed trovata"));
        assertFalse(c.contains("snapshotWarning = r42SyncMessage(snapshotError)"));
        assertTrue(r.contains("runBounded(Context context, List<String> args, long timeoutSeconds)"));
        assertTrue(r.contains("process.waitFor(Math.max(10L, timeoutSeconds), TimeUnit.SECONDS)"));
    }
}
