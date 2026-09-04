package it.dossiersanitario.clinicadigitale.beta;

import static org.junit.Assert.assertArrayEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;
import java.util.zip.ZipOutputStream;

public class R25StreamClosedEyeTest {

    @Test
    public void zipEntryReaderDoesNotCloseZipStream() throws Exception {
        ByteArrayOutputStream packed = new ByteArrayOutputStream();
        try (ZipOutputStream out = new ZipOutputStream(packed)) {
            out.putNextEntry(new ZipEntry("first.json"));
            out.write("first".getBytes(StandardCharsets.UTF_8));
            out.closeEntry();
            out.putNextEntry(new ZipEntry("second.json"));
            out.write("second".getBytes(StandardCharsets.UTF_8));
            out.closeEntry();
        }

        try (ZipInputStream zip = new ZipInputStream(new ByteArrayInputStream(packed.toByteArray()))) {
            assertTrue(zip.getNextEntry() != null);
            assertArrayEquals("first".getBytes(StandardCharsets.UTF_8), R25ZipEntryReader.readEntry(zip));
            zip.closeEntry();
            assertTrue(zip.getNextEntry() != null);
            assertArrayEquals("second".getBytes(StandardCharsets.UTF_8), R25ZipEntryReader.readEntry(zip));
            zip.closeEntry();
        }
    }

    @Test
    public void bothImportPathsUseNonClosingEntryReader() throws Exception {
        String cloud = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R12CloudManager.java");

        int progressStart = cloud.indexOf("private static void importSnapshotWithProgress");
        int progressEnd = cloud.indexOf("private static void finalizeExistingConnectionProgress", progressStart);
        assertTrue(progressStart >= 0 && progressEnd > progressStart);
        String progressBlock = cloud.substring(progressStart, progressEnd);
        assertTrue(progressBlock.contains("R25ZipEntryReader.readEntry(zip)"));
        assertFalse(progressBlock.contains("readAll(zip)"));

        int legacyStart = cloud.indexOf("private static void importSnapshot(Context context");
        int legacyEnd = cloud.indexOf("private static void buildStandaloneSnapshot", legacyStart);
        assertTrue(legacyStart >= 0 && legacyEnd > legacyStart);
        String legacyBlock = cloud.substring(legacyStart, legacyEnd);
        assertTrue(legacyBlock.contains("R25ZipEntryReader.readEntry(zip)"));
        assertFalse(legacyBlock.contains("readAll(zip)"));
    }

    @Test
    public void startupPasswordHasVisibilityEye() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        int start = main.indexOf("private void showLoginScreen");
        int end = main.indexOf("private void attemptStartupLogin", start);
        assertTrue(start >= 0 && end > start);
        String block = main.substring(start, end);
        assertTrue(block.contains("android.widget.ImageButton passwordEye"));
        assertTrue(block.contains("TYPE_TEXT_VARIATION_VISIBLE_PASSWORD"));
        assertTrue(block.contains("Mostra password"));
        assertTrue(block.contains("Nascondi password"));
    }

    private static String read(String path) throws Exception {
        return new String(Files.readAllBytes(Paths.get(path)), StandardCharsets.UTF_8);
    }
}
