from pathlib import Path

BASE = Path('android-r3/app/src/main/java/it/dossiersanitario/clinicadigitale/beta')
CLOUD = BASE / 'R12CloudManager.java'
MAIN = BASE / 'R6MainActivity.java'


def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit(f'R14 patch failed: missing {label}')
    return text.replace(old, new, 1)


def patch_cloud():
    s = CLOUD.read_text(encoding='utf-8')

    if 'import android.util.Base64;' not in s:
        s = replace_once(s, 'import android.os.StatFs;\n', 'import android.os.StatFs;\nimport android.util.Base64;\n', 'android Base64 import')
    if 'import java.net.HttpURLConnection;' not in s:
        s = replace_once(s, 'import java.net.URLEncoder;\n', 'import java.net.URLEncoder;\nimport java.net.HttpURLConnection;\nimport java.net.URL;\n', 'HTTP imports')
    if 'import javax.crypto.Cipher;' not in s:
        marker = 'import java.util.zip.ZipOutputStream;\n'
        crypto_imports = (
            'import java.util.zip.ZipOutputStream;\n\n'
            'import javax.crypto.Cipher;\n'
            'import javax.crypto.SecretKeyFactory;\n'
            'import javax.crypto.spec.GCMParameterSpec;\n'
            'import javax.crypto.spec.PBEKeySpec;\n'
            'import javax.crypto.spec.SecretKeySpec;\n'
        )
        s = replace_once(s, marker, crypto_imports, 'crypto imports')

    constants_marker = '    private static volatile boolean syncing = false;\n'
    if 'FAMILY_RELAY_URL' not in s:
        constants = (
            '    private static volatile boolean syncing = false;\n'
            '    private static final String FAMILY_RELAY_URL = "https://clinica-digitale-family.dossiersanitario.workers.dev";\n'
            '    private static final String FAMILY_TEMP_PREFIX = "CDFA1.";\n'
            '    private static final String FAMILY_AAD = "ClinicaDigitale-FamilyTemporary-v1";\n'
        )
        s = replace_once(s, constants_marker, constants, 'family relay constants')

    start = s.find('    private static void showFamilyConnect(Activity activity, SharedPreferences prefs, boolean existingAccount) {')
    end = s.find('    private static void chooseInitialStorage(Activity activity, SharedPreferences prefs, JSONObject payload) {', start)
    if start < 0 or end < 0:
        raise SystemExit('R14 patch failed: family connect block not found')

    family_block = r'''    private static void showFamilyConnect(Activity activity, SharedPreferences prefs, boolean existingAccount) {
        LinearLayout form = dialogForm(activity);
        EditText familyPassword = field(activity, "Chiave Dossier · 15 caratteri", "");
        familyPassword.setInputType(android.text.InputType.TYPE_CLASS_TEXT | android.text.InputType.TYPE_TEXT_VARIATION_PASSWORD);
        form.addView(familyPassword);
        new AlertDialog.Builder(activity)
                .setTitle(existingAccount ? "Collega il mio account esistente" : "Collega un nuovo utente familiare")
                .setMessage(existingAccount
                        ? "1/2 · Inserisci la chiave Dossier di 15 caratteri generata dall’amministratore. Dopo la verifica userai nome utente e password del tuo account già esistente."
                        : "Inserisci la chiave Dossier di 15 caratteri ricevuta dall’amministratore. Non servono codici lunghi né credenziali MEGA.")
                .setView(form)
                .setNegativeButton("Annulla", null)
                .setPositiveButton("Verifica chiave", (d, w) -> {
                    String password = clean(familyPassword);
                    if (!validFamilyPassword(password)) {
                        Toast.makeText(activity, "La chiave Dossier deve contenere esattamente 15 caratteri, con lettere, numeri e almeno un carattere speciale.", Toast.LENGTH_LONG).show();
                        return;
                    }
                    runProgress(activity, "Verifica chiave Dossier", () -> {
                        JSONObject payload = fetchFamilyPackageFromRelay(password);
                        payload.put("existingAccountMode", existingAccount);
                        activity.runOnUiThread(() -> chooseInitialStorage(activity, prefs, payload));
                    });
                })
                .show();
    }

    private static boolean validFamilyPassword(String password) {
        if (password == null || password.length() != 15) return false;
        boolean letter = false, digit = false, special = false;
        for (int i = 0; i < password.length(); i++) {
            char c = password.charAt(i);
            if (Character.isLetter(c)) letter = true;
            else if (Character.isDigit(c)) digit = true;
            else special = true;
        }
        return letter && digit && special;
    }

    private static JSONObject fetchFamilyPackageFromRelay(String password) throws Exception {
        String inviteId = b64UrlNoPadding(MessageDigest.getInstance("SHA-256").digest(password.getBytes(StandardCharsets.UTF_8)));
        HttpURLConnection connection = null;
        try {
            connection = (HttpURLConnection) new URL(FAMILY_RELAY_URL + "/v1/invites/" + inviteId).openConnection();
            connection.setRequestMethod("GET");
            connection.setConnectTimeout(10000);
            connection.setReadTimeout(15000);
            connection.setUseCaches(false);
            connection.setRequestProperty("Accept", "application/json");
            int status = connection.getResponseCode();
            InputStream input = status >= 200 && status < 300 ? connection.getInputStream() : connection.getErrorStream();
            String body = readUtf8(input);
            if (status == 404) throw new Exception("Chiave Dossier non riconosciuta oppure accesso già scaduto.");
            if (status < 200 || status >= 300) throw new Exception("Il servizio di associazione familiare non è raggiungibile. Riprova tra poco.");
            JSONObject response = new JSONObject(body);
            String blob = response.optString("blob", "");
            if (blob.isEmpty()) throw new Exception("Accesso familiare non disponibile. Chiedi all’amministratore di generare una nuova chiave.");
            return openFamilyRelayBlob(blob, password);
        } catch (Exception e) {
            String message = String.valueOf(e.getMessage());
            if (message.contains("Chiave Dossier") || message.contains("servizio di associazione") || message.contains("Accesso familiare")) throw e;
            throw new Exception("Non è stato possibile verificare la chiave Dossier. Controlla la connessione e riprova.");
        } finally {
            if (connection != null) connection.disconnect();
        }
    }

    private static JSONObject openFamilyRelayBlob(String blob, String password) throws Exception {
        if (blob == null || !blob.startsWith(FAMILY_TEMP_PREFIX)) throw new Exception("Accesso familiare non riconosciuto.");
        try {
            JSONObject envelope = new JSONObject(new String(unb64Url(blob.substring(FAMILY_TEMP_PREFIX.length())), StandardCharsets.UTF_8));
            if (envelope.optInt("v", 0) != 1) throw new Exception("invalid envelope");
            byte[] salt = unb64Url(envelope.getString("salt"));
            byte[] iv = unb64Url(envelope.getString("iv"));
            byte[] encrypted = unb64Url(envelope.getString("data"));
            PBEKeySpec spec = new PBEKeySpec(password.toCharArray(), salt, 260000, 256);
            byte[] key = SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256").generateSecret(spec).getEncoded();
            Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
            cipher.init(Cipher.DECRYPT_MODE, new SecretKeySpec(key, "AES"), new GCMParameterSpec(128, iv));
            cipher.updateAAD(FAMILY_AAD.getBytes(StandardCharsets.UTF_8));
            JSONObject payload = new JSONObject(new String(cipher.doFinal(encrypted), StandardCharsets.UTF_8));
            if (!"family-temporary-access".equals(payload.optString("kind", "")) || payload.optInt("version", 0) < 1 || payload.optString("activationId", "").isEmpty() || payload.optJSONObject("cloud") == null || payload.optJSONObject("securityBundle") == null || payload.optString("joinSecret", "").isEmpty()) {
                throw new Exception("invalid package");
            }
            long expires = payload.optLong("expiresAtEpoch", 0L);
            if (expires > 0L && System.currentTimeMillis() / 1000L > expires) throw new Exception("Questo accesso familiare è scaduto. Chiedi all’amministratore di generarne uno nuovo.");
            return payload;
        } catch (Exception e) {
            String message = String.valueOf(e.getMessage());
            if (message.contains("scaduto")) throw e;
            throw new Exception("Chiave Dossier errata oppure accesso familiare non disponibile.");
        }
    }

    private static String b64UrlNoPadding(byte[] value) {
        return Base64.encodeToString(value, Base64.URL_SAFE | Base64.NO_WRAP | Base64.NO_PADDING);
    }

    private static byte[] unb64Url(String value) {
        String text = String.valueOf(value == null ? "" : value).replace('-', '+').replace('_', '/');
        while ((text.length() & 3) != 0) text += "=";
        return Base64.decode(text, Base64.DEFAULT);
    }

    private static String readUtf8(InputStream input) throws Exception {
        if (input == null) return "";
        try (InputStream in = input; ByteArrayOutputStream out = new ByteArrayOutputStream()) {
            byte[] buffer = new byte[8192];
            int read;
            while ((read = in.read(buffer)) >= 0) out.write(buffer, 0, read);
            return out.toString("UTF-8");
        }
    }

'''
    s = s[:start] + family_block + s[end:]
    CLOUD.write_text(s, encoding='utf-8')


def patch_main():
    s = MAIN.read_text(encoding='utf-8')
    s = s.replace('Android R13 TEST', 'Android R14 TEST')
    s = s.replace('Aiuto R13', 'Aiuto R14')
    s = s.replace('R13: struttura presente', 'R14: struttura presente')
    s = s.replace('R13 mantiene lo stesso pacchetto Android', 'R14 mantiene lo stesso pacchetto Android')
    s = s.replace('Installala sopra la R12', 'Installala sopra la R13')
    MAIN.write_text(s, encoding='utf-8')


patch_cloud()
patch_main()
print('R14 family password relay patch applied')
