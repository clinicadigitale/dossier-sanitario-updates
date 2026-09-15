from pathlib import Path
import re
import shutil

BASE = Path('android-r3/app/src/main/java/it/dossiersanitario/clinicadigitale/beta')
TEST = Path('android-r3/app/src/test/java/it/dossiersanitario/clinicadigitale/beta')
CLOUD = BASE / 'R12CloudManager.java'
BOUNDED = BASE / 'R30BoundedWindows.java'
GRADLE = Path('android-r3/app/build.gradle')

def require(text, needle, label):
    if needle not in text:
        raise SystemExit('R57 missing ' + label)

def method_slice(text, signature, label):
    start = text.find(signature)
    if start < 0:
        raise SystemExit('R57 missing ' + label)
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
        raise SystemExit('R57 unclosed ' + label)
    return start, end

shutil.copyfile(Path('android-r3/r57_src/R57BoundedGcmDecryptor.java'), BASE / 'R57BoundedGcmDecryptor.java')

cloud = CLOUD.read_text(encoding='utf-8')
old_call = 'R46Dsl5Decryptor.decrypt(encryptedPart, plainZip, recovery, (read, total) -> {'
new_call = 'R57BoundedGcmDecryptor.decrypt(encryptedPart, plainZip, recovery, (read, total) -> {'
require(cloud, old_call, 'R46 decrypt call')
cloud = cloud.replace(old_call, new_call, 1)

preflight = '        if (latest.size > 0 && freeBytes(root) < required) throw new Exception("Spazio insufficiente per aggiornare il Dossier: servono " + formatBytes(required) + ".");\n'
require(cloud, preflight, 'snapshot storage preflight')
internal = preflight + '''        long safeSnapshotSize = Math.max(0L, latest.size);
        long internalRequired = safeSnapshotSize > (Long.MAX_VALUE - 128L * MB) / 2L
                ? Long.MAX_VALUE
                : safeSnapshotSize * 2L + 128L * MB;
        long internalFree = freeBytes(context.getFilesDir());
        if (safeSnapshotSize > 0L && internalFree < internalRequired) {
            throw new Exception("Spazio interno insufficiente per aggiornare il Dossier: servono circa " + formatBytes(internalRequired) + " liberi durante l'aggiornamento.");
        }
'''
cloud = cloud.replace(preflight, internal, 1)

start, end = method_slice(cloud, '    public static void syncInteractiveR45(Activity activity, SharedPreferences prefs) {', 'syncInteractiveR45')
method = cloud[start:end]
old_catch = '''            } catch (Exception e) {
                activity.runOnUiThread(() -> {
                    dialog.dismiss();
                    new AlertDialog.Builder(activity).setTitle("Sincronizzazione non completata").setMessage(r42SyncMessage(e)).setPositiveButton("Chiudi", null).show();
                });
            }'''
new_catch = '''            } catch (Throwable failure) {
                final Exception e = failure instanceof Exception
                        ? (Exception) failure
                        : new Exception(failure instanceof OutOfMemoryError
                                ? "Memoria insufficiente durante l'aggiornamento del Dossier."
                                : "Errore interno durante l'aggiornamento del Dossier.", failure);
                activity.runOnUiThread(() -> {
                    if (dialog.isShowing()) dialog.dismiss();
                    if (!activity.isFinishing() && !activity.isDestroyed()) {
                        new AlertDialog.Builder(activity).setTitle("Sincronizzazione non completata").setMessage(r42SyncMessage(e)).setPositiveButton("Chiudi", null).show();
                    }
                });
            }'''
require(method, old_catch, 'R45 interactive catch')
method = method.replace(old_catch, new_catch, 1)
cloud = cloud[:start] + method + cloud[end:]
CLOUD.write_text(cloud, encoding='utf-8')

bounded = BOUNDED.read_text(encoding='utf-8')
old_data = '''            {"richiami_calendario.json", "calendarSuggestions", "Richiami e scadenze"},
            {"indice_documenti.json", "documents", "Indice documenti"}
    };'''
new_data = '''            {"richiami_calendario.json", "calendarSuggestions", "Richiami e scadenze"},
            {"indice_documenti.json", "documents", "Indice documenti"},
            {"dicom_studies.json", "dicomStudies", "Metadati studi DICOM"},
            {"immagini_associate.json", "mediaAttachments", "Metadati immagini associate"}
    };'''
require(bounded, old_data, 'R30 data map')
bounded = bounded.replace(old_data, new_data, 1)
BOUNDED.write_text(bounded, encoding='utf-8')

gradle = GRADLE.read_text(encoding='utf-8')
gradle = re.sub(r'versionCode\s+56\b', 'versionCode 57', gradle, count=1)
gradle = gradle.replace("versionName '1.0.0-android-r56-modern-media-parity-test'", "versionName '1.0.0-android-r57-sync-crash-media-fix-test'")
if 'versionCode 57' not in gradle:
    raise SystemExit('R57 versionCode bump failed')
GRADLE.write_text(gradle, encoding='utf-8')

for p in Path('android-r3/app/src/test').rglob('*.java'):
    s = p.read_text(encoding='utf-8')
    ns = s.replace('versionCode 56', 'versionCode 57').replace('versionCode = 56', 'versionCode = 57')
    ns = ns.replace('1.0.0-android-r56-modern-media-parity-test', '1.0.0-android-r57-sync-crash-media-fix-test')
    # R57 intentionally supersedes only the R46 GCM decrypt implementation.
    # Keep the old regression intent (streaming + real encrypted-byte progress),
    # but point it at the bounded authenticated implementation.
    ns = ns.replace('R46Dsl5Decryptor.java', 'R57BoundedGcmDecryptor.java')
    ns = ns.replace('R46Dsl5Decryptor.decrypt', 'R57BoundedGcmDecryptor.decrypt')
    ns = ns.replace('cipher.update(buffer, 0, n)', 'ctr.update(cipherBuf, 0, want, plainBuf, 0)')
    ns = ns.replace('cipher.doFinal()', 'ctr.doFinal()')
    ns = ns.replace('progress.onBytes(done, total)', 'progress.onBytes(done, Math.max(1L, cipherLength))')
    if ns != s:
        p.write_text(ns, encoding='utf-8')

TEST.mkdir(parents=True, exist_ok=True)
(TEST / 'R57SyncCrashMediaFixTest.java').write_text(r'''package it.dossiersanitario.clinicadigitale.beta;

import static org.junit.Assert.*;
import org.junit.Test;
import java.io.File;
import java.io.FileOutputStream;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.Base64;
import javax.crypto.Cipher;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;

public class R57SyncCrashMediaFixTest {
    private String read(String p) throws Exception { return new String(Files.readAllBytes(Paths.get(p)), StandardCharsets.UTF_8); }
    private static byte[] hex(String s) { byte[] out=new byte[s.length()/2]; for(int i=0;i<out.length;i++) out[i]=(byte)Integer.parseInt(s.substring(i*2,i*2+2),16); return out; }

    @Test public void boundedGhashMatchesNistGcmVector() throws Exception {
        byte[] key=new byte[16], iv=new byte[12];
        byte[] ciphertext=hex("0388dace60b6a392f328c2b971b2fe78");
        byte[] expectedTag=hex("ab6e47d42cec13bdf53a67b21257bddf");
        assertArrayEquals(expectedTag, R57BoundedGcmDecryptor.computeTagForTest(key,iv,ciphertext));
    }

    @Test public void boundedDecryptReadsExistingDsl5FormatExactly() throws Exception {
        byte[] key=hex("000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f");
        byte[] iv=hex("101112131415161718191a1b");
        byte[] plain=new byte[2*1024*1024+37];
        for(int i=0;i<plain.length;i++) plain[i]=(byte)(i*31+7);
        Cipher gcm=Cipher.getInstance("AES/GCM/NoPadding");
        gcm.init(Cipher.ENCRYPT_MODE,new SecretKeySpec(key,"AES"),new GCMParameterSpec(128,iv));
        byte[] packedPayload=gcm.doFinal(plain);
        String meta="{\"format\":\"DSL5-AESGCM\",\"version\":1,\"iv\":\""+Base64.getEncoder().encodeToString(iv)+"\"}";
        byte[] mb=meta.getBytes(StandardCharsets.UTF_8);
        File source=File.createTempFile("r57dsl5",".bin");
        File target=File.createTempFile("r57plain",".bin"); target.delete();
        try(FileOutputStream out=new FileOutputStream(source)){
            out.write("DSL5ENC1".getBytes(StandardCharsets.US_ASCII));
            out.write(ByteBuffer.allocate(4).putInt(mb.length).array()); out.write(mb); out.write(packedPayload);
        }
        try {
            R57BoundedGcmDecryptor.decrypt(source,target,key,null);
            assertArrayEquals(plain,Files.readAllBytes(target.toPath()));
        } finally { source.delete(); target.delete(); }
    }

    @Test public void syncUsesBoundedAuthenticatedDecryptAndThrowableGuard() throws Exception {
        String c=read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R12CloudManager.java");
        assertTrue(c.contains("R57BoundedGcmDecryptor.decrypt(encryptedPart, plainZip, recovery"));
        assertTrue(c.contains("catch (Throwable failure)"));
        assertTrue(c.contains("internalRequired"));
        assertTrue(c.contains("Spazio interno insufficiente"));
    }

    @Test public void boundedImporterCarriesImagingMetadataOnly() throws Exception {
        String b=read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R30BoundedWindows.java");
        assertTrue(b.contains("{\"dicom_studies.json\", \"dicomStudies\""));
        assertTrue(b.contains("{\"immagini_associate.json\", \"mediaAttachments\""));
        assertFalse(b.contains("dicom_originals"));
    }

    @Test public void r57IdentityIsUpgradeableOverR56() throws Exception {
        String g=read("build.gradle");
        assertTrue(g.contains("versionCode 57"));
        assertTrue(g.contains("1.0.0-android-r57-sync-crash-media-fix-test"));
    }
}
''', encoding='utf-8')

print('R57 bounded authenticated sync/media corrective patch applied')
