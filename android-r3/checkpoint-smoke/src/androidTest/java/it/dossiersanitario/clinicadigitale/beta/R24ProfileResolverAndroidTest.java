package it.dossiersanitario.clinicadigitale.beta;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

import android.content.Context;

import androidx.test.core.app.ApplicationProvider;
import androidx.test.ext.junit.runners.AndroidJUnit4;

import org.json.JSONArray;
import org.json.JSONObject;
import org.junit.Test;
import org.junit.runner.RunWith;

import java.io.File;
import java.io.FileOutputStream;
import java.nio.charset.StandardCharsets;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

@RunWith(AndroidJUnit4.class)
public class R24ProfileResolverAndroidTest {

    @Test
    public void genericAdministratorInviteResolvesAdministratorProfile() throws Exception {
        Context context = ApplicationProvider.getApplicationContext();
        File zipFile = new File(context.getCacheDir(), "r24_admin_profiles.zip");
        if (zipFile.exists()) zipFile.delete();

        JSONObject manifest = new JSONObject();
        JSONArray profiles = new JSONArray();
        profiles.put(new JSONObject().put("profileId", "profile_family").put("name", "Gaia Rossi"));
        profiles.put(new JSONObject().put("profileId", "profile_admin").put("name", "Daniele Rossi"));
        manifest.put("profiles", profiles);

        JSONObject family = new JSONObject()
                .put("id", "profile_family")
                .put("firstName", "Gaia")
                .put("lastName", "Rossi")
                .put("relation", "Familiare");
        JSONObject admin = new JSONObject()
                .put("id", "profile_admin")
                .put("firstName", "Daniele")
                .put("lastName", "Rossi")
                .put("relation", "Amministratore");

        try (ZipOutputStream zip = new ZipOutputStream(new FileOutputStream(zipFile))) {
            add(zip, "manifest.json", manifest.toString());
            add(zip, "profili/gaia/profile.json", family.toString());
            add(zip, "profili/daniele/profilo.json", admin.toString());
        }

        R24ProfileResolver.Result result = R24ProfileResolver.resolve(zipFile, "", true, "Nome account diverso");
        assertEquals("profile_admin", result.id);
        assertEquals("Daniele Rossi", result.name);
        assertTrue(zipFile.delete());
    }

    @Test
    public void explicitLinkedProfileRemainsAuthoritative() throws Exception {
        R24ProfileResolver.Result result = R24ProfileResolver.resolve(null, "profile_existing", false, "");
        assertEquals("profile_existing", result.id);
    }

    @Test(expected = Exception.class)
    public void nonAdministratorWithoutLinkedProfileIsRejected() throws Exception {
        Context context = ApplicationProvider.getApplicationContext();
        File zipFile = new File(context.getCacheDir(), "r24_empty.zip");
        try (ZipOutputStream zip = new ZipOutputStream(new FileOutputStream(zipFile))) {
            add(zip, "manifest.json", new JSONObject().put("profiles", new JSONArray()).toString());
        }
        try {
            R24ProfileResolver.resolve(zipFile, "", false, "Utente");
        } finally {
            zipFile.delete();
        }
    }

    private static void add(ZipOutputStream zip, String path, String text) throws Exception {
        zip.putNextEntry(new ZipEntry(path));
        zip.write(text.getBytes(StandardCharsets.UTF_8));
        zip.closeEntry();
    }
}
