package it.dossiersanitario.clinicadigitale.beta;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;

public class R30BoundedImportTest {
    private String read(String path) throws Exception {
        return new String(Files.readAllBytes(Paths.get(path)), StandardCharsets.UTF_8);
    }

    @Test public void cloudRoutesEveryExactWindowsImportThroughBoundedImporter() throws Exception {
        String cloud = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R12CloudManager.java");
        assertTrue(cloud.contains("R30BoundedWindows.importSnapshot(activity, prefs, cfg, verifiedZip, null)"));
        assertTrue(cloud.contains("R30BoundedWindows.importSnapshot(activity, prefs, cfg, verified, null)"));
        assertTrue(cloud.contains("R30BoundedWindows.importSnapshot(activity, prefs, cfg, verified, importProgress)"));
        assertFalse(cloud.contains("R27ExactWindows.importSnapshot(activity, prefs, cfg, verifiedZip)"));
        assertFalse(cloud.contains("R27ExactWindows.importSnapshot(activity, prefs, cfg, verified, importProgress)"));
    }

    @Test public void largePerProfileJsonIsStreamedToPrivateFilesInsteadOfSharedPreferences() throws Exception {
        String bounded = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R30BoundedWindows.java");
        assertTrue(bounded.contains("private static final String POINTER = \"@file:\""));
        assertTrue(bounded.contains("extract(zip, source, targetStage)"));
        assertTrue(bounded.contains("prefPointers.put(key(profileId, map[1]), POINTER + targetFinal.getAbsolutePath())"));
        assertFalse(bounded.contains("putArray(editor"));
        assertFalse(bounded.contains("new JSONObject(source.toString())"));
    }

    @Test public void documentsAreCopiedStreamingWithoutMaterializingTheDocumentIndex() throws Exception {
        String bounded = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R30BoundedWindows.java");
        assertTrue(bounded.contains("String docPrefix = folder + \"documenti/\""));
        assertTrue(bounded.contains("extract(zip, item.getValue(), target)"));
        assertTrue(bounded.contains("indice_documenti.json"));
        assertFalse(bounded.contains("readArray(zip, entries.get(folderForWork + \"indice_documenti.json\")).length()"));
    }

    @Test public void diskBackedArraysRemainCompatibleWithExistingSections() throws Exception {
        String exact = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R27ExactWindows.java");
        assertTrue(exact.contains("raw.startsWith(\"@file:\")"));
        assertTrue(exact.contains("R30BoundedWindows.readArrayFile"));
        assertTrue(exact.contains("static JSONArray documents(SharedPreferences prefs)"));
        assertTrue(exact.contains("static JSONArray therapies(SharedPreferences prefs)"));
        assertTrue(exact.contains("static JSONArray diagnoses(SharedPreferences prefs)"));
        assertTrue(exact.contains("static JSONArray measurements(SharedPreferences prefs)"));
    }

    @Test public void documentOpenResolvesStreamedOriginals() throws Exception {
        String exact = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R27ExactWindows.java");
        String bounded = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R30BoundedWindows.java");
        assertTrue(exact.contains("R30BoundedWindows.resolveDocumentFile(activity, doc)"));
        assertTrue(bounded.contains("File[] matches = docsDir.listFiles"));
        assertTrue(bounded.contains("name.startsWith(id + \"__\")"));
    }

    @Test public void importIsPromotedTransactionallyOnlyAfterFilesAreComplete() throws Exception {
        String bounded = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R30BoundedWindows.java");
        assertTrue(bounded.contains("STAGE_NAME"));
        assertTrue(bounded.contains("finalRoot.exists() && !finalRoot.renameTo(oldRoot)"));
        assertTrue(bounded.contains("!stageRoot.renameTo(finalRoot)"));
        assertTrue(bounded.contains("if (!editor.commit())"));
        assertTrue(bounded.contains("if (!stagePromoted) deleteTree(stageRoot)"));
    }

    @Test public void windowsUsersPreferencesActiveProfileAndHealthCardRemainImported() throws Exception {
        String bounded = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R30BoundedWindows.java");
        assertTrue(bounded.contains("preferenze/impostazioni.json"));
        assertTrue(bounded.contains("sicurezza/utenti_indicizzati.json"));
        assertTrue(bounded.contains("activeProfileId:"));
        assertTrue(bounded.contains("tessera_sanitaria/"));
        assertTrue(bounded.contains("r27_global_preferences_json"));
        assertTrue(bounded.contains("r27_active_profile_id"));
    }

    @Test public void existingRealProgressAndCrashGuardRemainActive() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        String cloud = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R12CloudManager.java");
        assertTrue(main.contains("progressBarStyleHorizontal"));
        assertTrue(main.contains("scaleR29(done, total, 0, 55)"));
        assertTrue(main.contains("scaleR29(done, total, 55, 44)"));
        assertTrue(main.contains("showR29WindowsMigrationFailure"));
        assertTrue(cloud.contains("catch (Throwable failure)"));
    }

    @Test public void versionIsR30BoundedImportTest() throws Exception {
        String gradle = read("build.gradle");
        assertTrue(gradle.contains("versionCode 30"));
        assertTrue(gradle.contains("versionName '1.0.0-android-r30-bounded-import-test'"));
    }
}
