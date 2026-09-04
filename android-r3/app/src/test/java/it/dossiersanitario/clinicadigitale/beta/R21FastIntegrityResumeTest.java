package it.dossiersanitario.clinicadigitale.beta;

import static org.junit.Assert.assertArrayEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

import org.junit.Test;

import java.io.ByteArrayOutputStream;
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

public class R21FastIntegrityResumeTest {

    @Test
    public void fastDsl5DecryptsAndAuthenticatesInOnePass() throws Exception {
        byte[] recovery = new byte[32];
        for (int i = 0; i < recovery.length; i++) recovery[i] = (byte) (i * 13 + 9);
        byte[] plain = new byte[12 * 1024 * 1024];
        for (int i = 0; i < plain.length; i++) plain[i] = (byte) (i * 31 + (i >>> 11));

        File snapshot = makeDsl5(plain, recovery);
        File out = File.createTempFile("r21_plain_", ".zip");
        try {
            R21FastDsl5.decryptVerified(snapshot, out, recovery, null);
            assertArrayEquals(plain, Files.readAllBytes(out.toPath()));
        } finally {
            snapshot.delete();
            out.delete();
        }
    }

    @Test
    public void corruptedGcmNeverBecomesVerifiedOutput() throws Exception {
        byte[] recovery = new byte[32];
        for (int i = 0; i < recovery.length; i++) recovery[i] = (byte) (0x21 + i);
        byte[] plain = new byte[2 * 1024 * 1024];
        for (int i = 0; i < plain.length; i++) plain[i] = (byte) (i * 7 + 3);

        File snapshot = makeDsl5(plain, recovery);
        byte[] packed = Files.readAllBytes(snapshot.toPath());
        packed[packed.length - 1] ^= 0x55;
        Files.write(snapshot.toPath(), packed);
        File out = File.createTempFile("r21_bad_", ".zip");
        out.delete();
        try {
            try {
                R21FastDsl5.decryptVerified(snapshot, out, recovery, null);
                fail("Corrupted GCM snapshot accepted");
            } catch (Exception expected) {
                assertFalse("Unauthenticated plaintext was left behind", out.exists());
            }
        } finally {
            snapshot.delete();
            out.delete();
        }
    }

    @Test
    public void cloudFlowUsesSingleDecryptAndPreservesAuthenticatedResume() throws Exception {
        String cloud = new String(Files.readAllBytes(Paths.get("src/main/java/it/dossiersanitario/clinicadigitale/beta/R12CloudManager.java")), StandardCharsets.UTF_8);

        assertTrue(cloud.contains("verifiedZip = prepareVerifiedSnapshotProgress(activity, progress, partialRef, recovery)"));
        assertTrue(cloud.contains("importSnapshotWithProgress(activity, progress, prefs, cfg, verifiedZip)"));
        assertFalse(cloud.contains("importSnapshotWithProgress(activity, progress, prefs, cfg, partialRef, recovery)"));
        assertTrue(cloud.contains("R21FastDsl5.decryptVerified(snapshot, verified, recovery"));
        assertTrue(cloud.contains("In questa fase possono essere necessari diversi minuti."));
        assertTrue(cloud.contains("Importazione del Dossier incompleta. Il dispositivo è già autenticato: non devi reinserire chiave Dossier, account o TOTP."));
        assertTrue(cloud.contains("R20CheckpointCrypto.protect(context, state.toString())"));
        assertTrue(cloud.contains("R20CheckpointCrypto.unprotect(activity, protectedState)"));

        int totp = cloud.indexOf("if (!R12Crypto.verifyTotp(secret, clean(otp)))");
        int persist = cloud.indexOf("persistExistingImportCheckpoint(activity, prefs, payload, cfg, choice, snap, account);", totp);
        int start = cloud.indexOf("safeStartExistingImportProgress(activity, prefs, payload, cfg, choice, snap, account);", persist);
        assertTrue("TOTP branch not found", totp >= 0);
        assertTrue("Authenticated checkpoint is not persisted after TOTP", persist > totp);
        assertTrue("Import starts before authenticated checkpoint is persisted", start > persist);
    }

    @Test
    public void progressUsesExactlyOneDecimalForMegabytes() {
        long bytes = 43L * 1024L * 1024L + 6L * 1024L * 1024L / 10L;
        assertTrue("43,6 MB".equals(R12CloudManager.formatProgressBytesOneDecimal(bytes)));
    }

    private static File makeDsl5(byte[] plain, byte[] recovery) throws Exception {
        byte[] iv = new byte[12];
        for (int i = 0; i < iv.length; i++) iv[i] = (byte) (0x41 + i);
        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        cipher.init(Cipher.ENCRYPT_MODE, new SecretKeySpec(recovery, "AES"), new GCMParameterSpec(128, iv));
        byte[] encrypted = cipher.doFinal(plain);

        String metadata = "{\"format\":\"DSL5-AESGCM\",\"version\":1,\"iv\":\""
                + Base64.getEncoder().encodeToString(iv) + "\",\"kind\":\"r21-test\"}";
        byte[] metaBytes = metadata.getBytes(StandardCharsets.UTF_8);

        ByteArrayOutputStream packed = new ByteArrayOutputStream();
        packed.write("DSL5ENC1".getBytes(StandardCharsets.US_ASCII));
        packed.write(ByteBuffer.allocate(4).putInt(metaBytes.length).array());
        packed.write(metaBytes);
        packed.write(encrypted);

        File snapshot = File.createTempFile("r21_snapshot_", ".dsl5");
        try (FileOutputStream out = new FileOutputStream(snapshot)) {
            out.write(packed.toByteArray());
        }
        return snapshot;
    }
}
