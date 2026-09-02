package it.dossiersanitario.clinicadigitale.beta;

import android.content.Context;
import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;
import android.util.Base64;

import org.json.JSONObject;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.InputStream;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.security.KeyStore;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.text.Normalizer;
import java.time.Instant;
import java.util.Locale;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import javax.crypto.Cipher;
import javax.crypto.CipherInputStream;
import javax.crypto.KeyGenerator;
import javax.crypto.Mac;
import javax.crypto.SecretKey;
import javax.crypto.SecretKeyFactory;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.PBEKeySpec;
import javax.crypto.spec.SecretKeySpec;

public final class R12Crypto {
    private static final SecureRandom RNG = new SecureRandom();
    private static final int PBKDF2_ITERATIONS = 260000;
    private static final String FAMILY_PREFIX = "CDFA1.";
    private static final byte[] FAMILY_AAD = "ClinicaDigitale-FamilyTemporary-v1".getBytes(StandardCharsets.UTF_8);
    private static final byte[] DSL_MAGIC = "DSL5ENC1".getBytes(StandardCharsets.US_ASCII);
    private static final String KEYSTORE = "AndroidKeyStore";
    private static final String KEY_ALIAS = "clinica_digitale_r12_cloud_secret";
    private static final String BASE32 = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";

    private R12Crypto() {}

    public static byte[] randomBytes(int count) {
        byte[] out = new byte[count];
        RNG.nextBytes(out);
        return out;
    }

    public static String randomHex(int bytes) {
        byte[] raw = randomBytes(bytes);
        StringBuilder b = new StringBuilder(raw.length * 2);
        for (byte value : raw) b.append(String.format(Locale.ROOT, "%02x", value & 0xff));
        return b.toString();
    }

    public static String b64Url(byte[] raw) {
        return Base64.encodeToString(raw, Base64.URL_SAFE | Base64.NO_WRAP | Base64.NO_PADDING);
    }

    public static byte[] unb64Url(String value) {
        return Base64.decode(String.valueOf(value), Base64.URL_SAFE | Base64.NO_WRAP | Base64.NO_PADDING);
    }

    public static String b64(byte[] raw) {
        return Base64.encodeToString(raw, Base64.NO_WRAP);
    }

    public static byte[] unb64(String value) {
        return Base64.decode(String.valueOf(value), Base64.NO_WRAP);
    }

    public static byte[] pbkdf2(String password, byte[] salt, int bits) throws Exception {
        PBEKeySpec spec = new PBEKeySpec(String.valueOf(password).toCharArray(), salt, PBKDF2_ITERATIONS, bits);
        try {
            return SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256").generateSecret(spec).getEncoded();
        } finally {
            spec.clearPassword();
        }
    }

    public static JSONObject openFamilyPackage(String code, String temporaryPassword) throws Exception {
        String text = String.valueOf(code == null ? "" : code).trim();
        Matcher matcher = Pattern.compile("CDFA1\\.[A-Za-z0-9_-]+").matcher(text);
        if (matcher.find()) text = matcher.group();
        if (!text.startsWith(FAMILY_PREFIX)) throw new Exception("Codice di accesso provvisorio non riconosciuto.");
        JSONObject envelope;
        try {
            byte[] outer = unb64Url(text.substring(FAMILY_PREFIX.length()));
            envelope = new JSONObject(new String(outer, StandardCharsets.UTF_8));
        } catch (Exception error) {
            throw new Exception("Codice di accesso provvisorio non valido.");
        }
        if (envelope.optInt("v", 0) != 1 || !envelope.has("salt") || !envelope.has("iv") || !envelope.has("data")) {
            throw new Exception("Codice di accesso provvisorio incompleto.");
        }
        try {
            byte[] salt = unb64Url(envelope.getString("salt"));
            byte[] iv = unb64Url(envelope.getString("iv"));
            byte[] keyRaw = pbkdf2(temporaryPassword, salt, 256);
            Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
            cipher.init(Cipher.DECRYPT_MODE, new SecretKeySpec(keyRaw, "AES"), new GCMParameterSpec(128, iv));
            cipher.updateAAD(FAMILY_AAD);
            byte[] plain = cipher.doFinal(unb64Url(envelope.getString("data")));
            JSONObject payload = new JSONObject(new String(plain, StandardCharsets.UTF_8));
            if (!"family-temporary-access".equals(payload.optString("kind")) || payload.optInt("version", 0) != 1 || !payload.has("activationId") || !payload.has("cloud")) {
                throw new Exception("Pacchetto di accesso non valido.");
            }
            long expires = payload.optLong("expiresAtEpoch", 0L);
            if (expires > 0 && System.currentTimeMillis() / 1000L > expires) {
                throw new Exception("Questo accesso provvisorio è scaduto. Chiedi all’amministratore di generarne uno nuovo.");
            }
            return payload;
        } catch (Exception error) {
            String message = String.valueOf(error.getMessage());
            if (message.contains("scaduto") || message.contains("non valido")) throw error;
            throw new Exception("Password provvisoria errata oppure codice di accesso danneggiato.");
        }
    }

    public static byte[] encryptDsl5(byte[] plain, byte[] keyRaw, JSONObject extraMetadata) throws Exception {
        byte[] iv = randomBytes(12);
        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        cipher.init(Cipher.ENCRYPT_MODE, new SecretKeySpec(keyRaw, "AES"), new GCMParameterSpec(128, iv));
        byte[] encrypted = cipher.doFinal(plain);
        JSONObject meta = new JSONObject();
        meta.put("format", "DSL5-AESGCM");
        meta.put("version", 1);
        meta.put("createdAt", Instant.now().toString());
        meta.put("iv", b64(iv));
        if (extraMetadata != null) {
            java.util.Iterator<String> it = extraMetadata.keys();
            while (it.hasNext()) {
                String key = it.next();
                meta.put(key, extraMetadata.opt(key));
            }
        }
        byte[] metaBytes = meta.toString().getBytes(StandardCharsets.UTF_8);
        ByteArrayOutputStream out = new ByteArrayOutputStream(12 + metaBytes.length + encrypted.length);
        out.write(DSL_MAGIC);
        out.write(ByteBuffer.allocate(4).putInt(metaBytes.length).array());
        out.write(metaBytes);
        out.write(encrypted);
        return out.toByteArray();
    }

    public static byte[] decryptDsl5(byte[] packed, byte[] keyRaw) throws Exception {
        try (InputStream in = openDsl5Stream(new ByteArrayInputStream(packed), keyRaw); ByteArrayOutputStream out = new ByteArrayOutputStream()) {
            byte[] buf = new byte[65536];
            int n;
            while ((n = in.read(buf)) >= 0) out.write(buf, 0, n);
            return out.toByteArray();
        }
    }

    public static InputStream openDsl5File(File file, byte[] keyRaw) throws Exception {
        return openDsl5Stream(new FileInputStream(file), keyRaw);
    }

    private static InputStream openDsl5Stream(InputStream source, byte[] keyRaw) throws Exception {
        byte[] header = readExact(source, 12);
        for (int i = 0; i < DSL_MAGIC.length; i++) if (header[i] != DSL_MAGIC[i]) throw new Exception("Formato cifrato non riconosciuto");
        int metaLength = ByteBuffer.wrap(header, 8, 4).getInt();
        if (metaLength <= 0 || metaLength > 1024 * 1024) throw new Exception("Metadati archivio non validi");
        byte[] metaBytes = readExact(source, metaLength);
        JSONObject meta = new JSONObject(new String(metaBytes, StandardCharsets.UTF_8));
        if (!"DSL5-AESGCM".equals(meta.optString("format"))) throw new Exception("Formato archivio cloud non valido");
        byte[] iv = unb64(meta.getString("iv"));
        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        cipher.init(Cipher.DECRYPT_MODE, new SecretKeySpec(keyRaw, "AES"), new GCMParameterSpec(128, iv));
        return new CipherInputStream(source, cipher);
    }

    private static byte[] readExact(InputStream in, int length) throws Exception {
        byte[] out = new byte[length];
        int offset = 0;
        while (offset < length) {
            int n = in.read(out, offset, length - offset);
            if (n < 0) throw new Exception("Archivio cifrato incompleto");
            offset += n;
        }
        return out;
    }

    public static String protectSecret(Context context, String plain) throws Exception {
        SecretKey key = localSecretKey();
        byte[] iv = randomBytes(12);
        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        cipher.init(Cipher.ENCRYPT_MODE, key, new GCMParameterSpec(128, iv));
        byte[] encrypted = cipher.doFinal(String.valueOf(plain).getBytes(StandardCharsets.UTF_8));
        ByteArrayOutputStream out = new ByteArrayOutputStream(iv.length + encrypted.length);
        out.write(iv);
        out.write(encrypted);
        return b64(out.toByteArray());
    }

    public static String unprotectSecret(Context context, String packed) throws Exception {
        byte[] all = unb64(packed);
        if (all.length < 13) throw new Exception("Segreto locale non valido");
        byte[] iv = java.util.Arrays.copyOfRange(all, 0, 12);
        byte[] encrypted = java.util.Arrays.copyOfRange(all, 12, all.length);
        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        cipher.init(Cipher.DECRYPT_MODE, localSecretKey(), new GCMParameterSpec(128, iv));
        return new String(cipher.doFinal(encrypted), StandardCharsets.UTF_8);
    }

    private static SecretKey localSecretKey() throws Exception {
        KeyStore store = KeyStore.getInstance(KEYSTORE);
        store.load(null);
        if (store.containsAlias(KEY_ALIAS)) return (SecretKey) store.getKey(KEY_ALIAS, null);
        KeyGenerator generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, KEYSTORE);
        generator.init(new KeyGenParameterSpec.Builder(KEY_ALIAS, KeyProperties.PURPOSE_ENCRYPT | KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setKeySize(256)
                .build());
        return generator.generateKey();
    }

    public static String normalizeUsername(String value) {
        return String.valueOf(value == null ? "" : value).trim().replaceAll("\\s+", " ").toLowerCase(Locale.ROOT);
    }

    public static String normalizeRecoveryAnswer(String value) {
        String text = Normalizer.normalize(String.valueOf(value == null ? "" : value), Normalizer.Form.NFKC).trim().toLowerCase(Locale.ROOT);
        return text.replaceAll("\\s+", " ");
    }

    public static String passwordHash(String password, byte[] salt) throws Exception {
        return b64Url(pbkdf2(password, salt, 256));
    }

    public static String portableMfaEnvelope(String secret, String password) throws Exception {
        byte[] raw = secret.getBytes(StandardCharsets.US_ASCII);
        byte[] salt = randomBytes(16);
        byte[] nonce = randomBytes(16);
        byte[] material = pbkdf2(password, salt, 512);
        byte[] encKey = java.util.Arrays.copyOfRange(material, 0, 32);
        byte[] macKey = java.util.Arrays.copyOfRange(material, 32, 64);
        byte[] stream = mfaStream(encKey, nonce, raw.length);
        byte[] cipherText = new byte[raw.length];
        for (int i = 0; i < raw.length; i++) cipherText[i] = (byte) (raw[i] ^ stream[i]);
        Mac mac = Mac.getInstance("HmacSHA256");
        mac.init(new SecretKeySpec(macKey, "HmacSHA256"));
        ByteArrayOutputStream signed = new ByteArrayOutputStream();
        signed.write("Dossier-MFA-V1\0".getBytes(StandardCharsets.ISO_8859_1));
        signed.write(salt); signed.write(nonce); signed.write(cipherText);
        byte[] tag = mac.doFinal(signed.toByteArray());
        ByteArrayOutputStream packed = new ByteArrayOutputStream();
        packed.write(salt); packed.write(nonce); packed.write(cipherText); packed.write(tag);
        return "pwv1:" + b64Url(packed.toByteArray());
    }

    private static byte[] mfaStream(byte[] key, byte[] nonce, int length) throws Exception {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        int counter = 0;
        while (out.size() < length) {
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(key, "HmacSHA256"));
            ByteArrayOutputStream data = new ByteArrayOutputStream();
            data.write("Dossier-MFA-ENC\0".getBytes(StandardCharsets.ISO_8859_1));
            data.write(nonce);
            data.write(ByteBuffer.allocate(4).putInt(counter++).array());
            out.write(mac.doFinal(data.toByteArray()));
        }
        return java.util.Arrays.copyOf(out.toByteArray(), length);
    }

    public static String newTotpSecret() {
        return base32Encode(randomBytes(20));
    }

    private static String base32Encode(byte[] data) {
        StringBuilder out = new StringBuilder((data.length * 8 + 4) / 5);
        int buffer = 0, bits = 0;
        for (byte b : data) {
            buffer = (buffer << 8) | (b & 0xff);
            bits += 8;
            while (bits >= 5) {
                out.append(BASE32.charAt((buffer >> (bits - 5)) & 31));
                bits -= 5;
            }
        }
        if (bits > 0) out.append(BASE32.charAt((buffer << (5 - bits)) & 31));
        return out.toString();
    }

    public static boolean verifyTotp(String secret, String token) {
        String clean = String.valueOf(token == null ? "" : token).replaceAll("\\D", "");
        if (clean.length() != 6) return false;
        long now = System.currentTimeMillis() / 1000L;
        for (long offset : new long[]{-60, -30, 0, 30, 60}) {
            try {
                if (totp(secret, now + offset).equals(clean)) return true;
            } catch (Exception ignored) {}
        }
        return false;
    }

    private static String totp(String secret, long epochSeconds) throws Exception {
        byte[] key = base32Decode(secret);
        byte[] counter = ByteBuffer.allocate(8).putLong(epochSeconds / 30L).array();
        Mac mac = Mac.getInstance("HmacSHA1");
        mac.init(new SecretKeySpec(key, "HmacSHA1"));
        byte[] digest = mac.doFinal(counter);
        int offset = digest[digest.length - 1] & 0x0f;
        int value = ((digest[offset] & 0x7f) << 24) | ((digest[offset + 1] & 0xff) << 16) | ((digest[offset + 2] & 0xff) << 8) | (digest[offset + 3] & 0xff);
        return String.format(Locale.ROOT, "%06d", value % 1000000);
    }

    private static byte[] base32Decode(String text) throws Exception {
        String clean = String.valueOf(text).replace("=", "").toUpperCase(Locale.ROOT);
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        int buffer = 0, bits = 0;
        for (int i = 0; i < clean.length(); i++) {
            int value = BASE32.indexOf(clean.charAt(i));
            if (value < 0) throw new Exception("Base32 non valido");
            buffer = (buffer << 5) | value;
            bits += 5;
            if (bits >= 8) {
                out.write((buffer >> (bits - 8)) & 0xff);
                bits -= 8;
            }
        }
        return out.toByteArray();
    }

    public static String[] recoveryCodes() {
        String alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
        String[] out = new String[10];
        for (int n = 0; n < out.length; n++) {
            StringBuilder raw = new StringBuilder();
            for (int i = 0; i < 12; i++) raw.append(alphabet.charAt(RNG.nextInt(alphabet.length())));
            out[n] = raw.substring(0, 4) + "-" + raw.substring(4, 8) + "-" + raw.substring(8);
        }
        return out;
    }

    public static String recoveryCodeHash(String code) throws Exception {
        String normalized = String.valueOf(code == null ? "" : code).toUpperCase(Locale.ROOT).replaceAll("[^A-Z0-9]", "");
        return hex(MessageDigest.getInstance("SHA-256").digest(normalized.getBytes(StandardCharsets.US_ASCII)));
    }

    public static String sha256Hex(byte[] data) throws Exception {
        return hex(MessageDigest.getInstance("SHA-256").digest(data));
    }

    private static String hex(byte[] raw) {
        StringBuilder out = new StringBuilder(raw.length * 2);
        for (byte b : raw) out.append(String.format(Locale.ROOT, "%02x", b & 0xff));
        return out.toString();
    }
}
