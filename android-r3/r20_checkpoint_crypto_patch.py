from pathlib import Path

BASE = Path('android-r3/app/src/main/java/it/dossiersanitario/clinicadigitale/beta')
CLOUD = BASE / 'R12CloudManager.java'
MAIN = BASE / 'R6MainActivity.java'
GRADLE = Path('android-r3/app/build.gradle')
CRYPTO = BASE / 'R20CheckpointCrypto.java'


def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit(f'R20 patch failed: missing {label}')
    return text.replace(old, new, 1)


CRYPTO.write_text(r'''package it.dossiersanitario.clinicadigitale.beta;

import android.content.Context;
import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;
import android.util.Base64;

import java.nio.charset.StandardCharsets;
import java.security.KeyStore;
import java.security.SecureRandom;

import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;

final class R20CheckpointCrypto {
    private static final String KEYSTORE = "AndroidKeyStore";
    private static final String ALIAS = "clinica_digitale_r20_import_checkpoint";
    private static final String PREFIX = "R20K1.";
    private static final SecureRandom RNG = new SecureRandom();

    private R20CheckpointCrypto() {}

    static String protect(Context context, String plain) throws Exception {
        SecretKey key = usableKey(true);
        byte[] iv = new byte[12];
        RNG.nextBytes(iv);
        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        cipher.init(Cipher.ENCRYPT_MODE, key, new GCMParameterSpec(128, iv));
        byte[] encrypted = cipher.doFinal(String.valueOf(plain).getBytes(StandardCharsets.UTF_8));
        byte[] packed = new byte[iv.length + encrypted.length];
        System.arraycopy(iv, 0, packed, 0, iv.length);
        System.arraycopy(encrypted, 0, packed, iv.length, encrypted.length);
        String out = PREFIX + Base64.encodeToString(packed, Base64.NO_WRAP);

        // Self-test on the exact value before it is persisted.
        String roundTrip = unprotect(context, out);
        if (!String.valueOf(plain).equals(roundTrip)) throw new Exception("Autoverifica cifratura checkpoint non riuscita");
        return out;
    }

    static String unprotect(Context context, String packed) throws Exception {
        String text = String.valueOf(packed == null ? "" : packed).trim();
        if (!text.startsWith(PREFIX)) throw new Exception("Checkpoint locale non riconosciuto");
        byte[] all = Base64.decode(text.substring(PREFIX.length()), Base64.NO_WRAP);
        if (all.length < 29) throw new Exception("Checkpoint locale incompleto");
        byte[] iv = java.util.Arrays.copyOfRange(all, 0, 12);
        byte[] encrypted = java.util.Arrays.copyOfRange(all, 12, all.length);
        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        cipher.init(Cipher.DECRYPT_MODE, usableKey(false), new GCMParameterSpec(128, iv));
        return new String(cipher.doFinal(encrypted), StandardCharsets.UTF_8);
    }

    static boolean runtimeSelfTest(Context context) {
        try {
            String probe = "checkpoint-self-test-" + System.nanoTime();
            return probe.equals(unprotect(context, protect(context, probe)));
        } catch (Throwable e) {
            return false;
        }
    }

    private static SecretKey usableKey(boolean allowRepair) throws Exception {
        KeyStore store = KeyStore.getInstance(KEYSTORE);
        store.load(null);
        if (store.containsAlias(ALIAS)) {
            try {
                java.security.Key k = store.getKey(ALIAS, null);
                if (k instanceof SecretKey) return (SecretKey) k;
            } catch (Throwable broken) {
                if (!allowRepair) throw broken instanceof Exception ? (Exception) broken : new Exception(broken);
            }
            if (allowRepair) {
                try { store.deleteEntry(ALIAS); } catch (Throwable ignored) {}
            }
        }
        if (!allowRepair) throw new Exception("Chiave locale checkpoint non disponibile");

        Exception last = null;
        for (int bits : new int[]{256, 128}) {
            try {
                KeyGenerator generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, KEYSTORE);
                generator.init(new KeyGenParameterSpec.Builder(ALIAS, KeyProperties.PURPOSE_ENCRYPT | KeyProperties.PURPOSE_DECRYPT)
                        .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                        .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                        .setKeySize(bits)
                        .build());
                SecretKey generated = generator.generateKey();
                if (generated != null) return generated;
            } catch (Exception e) {
                last = e;
                try { store.deleteEntry(ALIAS); } catch (Throwable ignored) {}
            }
        }
        throw last == null ? new Exception("Impossibile creare la chiave locale checkpoint") : last;
    }
}
''', encoding='utf-8')

s = CLOUD.read_text(encoding='utf-8')
s = replace_once(
    s,
    '        String protectedState = R12Crypto.protectSecret(context, state.toString());\n',
    '        String protectedState = R20CheckpointCrypto.protect(context, state.toString());\n',
    'checkpoint protect'
)
s = replace_once(
    s,
    '            JSONObject state = new JSONObject(R12Crypto.unprotectSecret(activity, protectedState));\n',
    '            JSONObject state = new JSONObject(R20CheckpointCrypto.unprotect(activity, protectedState));\n',
    'checkpoint unprotect'
)
old_catch = '''                    } catch (Exception e) {\n                        Toast.makeText(activity, "Non è stato possibile memorizzare il collegamento del dispositivo.", Toast.LENGTH_LONG).show();\n                    }\n'''
new_catch = '''                    } catch (Exception e) {\n                        String detail = String.valueOf(e.getMessage());\n                        Toast.makeText(activity, "Memorizzazione collegamento non riuscita: " + (detail == null || detail.trim().isEmpty() ? e.getClass().getSimpleName() : detail), Toast.LENGTH_LONG).show();\n                    }\n'''
s = replace_once(s, old_catch, new_catch, 'checkpoint error visibility')
CLOUD.write_text(s, encoding='utf-8')

m = MAIN.read_text(encoding='utf-8')
m = m.replace('Android R19 TEST', 'Android R20 TEST')
m = m.replace('Aiuto R19', 'Aiuto R20')
m = m.replace('R19: struttura presente', 'R20: struttura presente')
m = m.replace('R19 mantiene lo stesso pacchetto Android', 'R20 mantiene lo stesso pacchetto Android')
m = m.replace('Installala sopra la R18', 'Installala sopra la R19')
MAIN.write_text(m, encoding='utf-8')

g = GRADLE.read_text(encoding='utf-8')
g = replace_once(g, 'versionCode 19', 'versionCode 20', 'versionCode')
g = replace_once(g, "versionName '1.0.0-android-r19-test'", "versionName '1.0.0-android-r20-test'", 'versionName')
GRADLE.write_text(g, encoding='utf-8')

print('R20 dedicated checkpoint crypto patch applied')
