from pathlib import Path

BASE = Path('android-r3/app/src/main/java/it/dossiersanitario/clinicadigitale/beta')
CLOUD = BASE / 'R12CloudManager.java'
MAIN = BASE / 'R6MainActivity.java'


def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit(f'R15 patch failed: missing {label}')
    return text.replace(old, new, 1)


def patch_cloud():
    s = CLOUD.read_text(encoding='utf-8')

    if 'import android.text.method.HideReturnsTransformationMethod;' not in s:
        s = replace_once(
            s,
            'import android.os.StatFs;\n',
            'import android.os.StatFs;\nimport android.text.method.HideReturnsTransformationMethod;\nimport android.text.method.PasswordTransformationMethod;\n',
            'password transformation imports'
        )
    if 'import android.view.MotionEvent;' not in s:
        s = replace_once(s, 'import android.view.Gravity;\n', 'import android.view.Gravity;\nimport android.view.MotionEvent;\n', 'motion import')

    helper_marker = '    private static void showFamilyConnect(Activity activity, SharedPreferences prefs, boolean existingAccount) {'
    if helper_marker not in s:
        raise SystemExit('R15 patch failed: family connect marker not found')
    eye_helper = r'''    private static void attachPasswordEye(Activity activity, EditText field) {
        field.setTransformationMethod(PasswordTransformationMethod.getInstance());
        field.setCompoundDrawablesWithIntrinsicBounds(0, 0, android.R.drawable.ic_menu_view, 0);
        field.setCompoundDrawablePadding(dp(activity, 8));
        field.setContentDescription("Password nascosta. Tocca l'occhio per mostrarla.");
        field.setOnTouchListener((view, event) -> {
            if (event.getAction() != MotionEvent.ACTION_UP) return false;
            android.graphics.drawable.Drawable right = field.getCompoundDrawables()[2];
            if (right == null) return false;
            float threshold = field.getWidth() - field.getPaddingRight() - right.getBounds().width() - dp(activity, 12);
            if (event.getX() < threshold) return false;
            int cursor = Math.max(0, field.getSelectionStart());
            boolean hidden = field.getTransformationMethod() instanceof PasswordTransformationMethod;
            field.setTransformationMethod(hidden ? HideReturnsTransformationMethod.getInstance() : PasswordTransformationMethod.getInstance());
            field.setSelection(Math.min(cursor, field.length()));
            field.setContentDescription(hidden ? "Password visibile. Tocca l'occhio per nasconderla." : "Password nascosta. Tocca l'occhio per mostrarla.");
            return true;
        });
    }

'''
    s = s.replace(helper_marker, eye_helper + helper_marker, 1)

    s = replace_once(
        s,
        '        familyPassword.setInputType(android.text.InputType.TYPE_CLASS_TEXT | android.text.InputType.TYPE_TEXT_VARIATION_PASSWORD);\n        form.addView(familyPassword);',
        '        familyPassword.setInputType(android.text.InputType.TYPE_CLASS_TEXT | android.text.InputType.TYPE_TEXT_VARIATION_PASSWORD);\n        attachPasswordEye(activity, familyPassword);\n        form.addView(familyPassword);',
        'family password eye'
    )
    s = replace_once(
        s,
        '        password.setInputType(android.text.InputType.TYPE_CLASS_TEXT | android.text.InputType.TYPE_TEXT_VARIATION_PASSWORD);\n        form.addView(username); form.addView(password);',
        '        password.setInputType(android.text.InputType.TYPE_CLASS_TEXT | android.text.InputType.TYPE_TEXT_VARIATION_PASSWORD);\n        attachPasswordEye(activity, password);\n        form.addView(username); form.addView(password);',
        'existing account password eye'
    )

    start = s.find('    private static void prepareExistingAccount(Activity activity, SharedPreferences prefs, JSONObject payload, JSONObject cfg, StorageChoice choice, SnapshotInfo snap, String username, String password) throws Exception {')
    end = s.find('    private static JSONObject findExistingAccount(File snapshot, byte[] recovery, String username) throws Exception {', start)
    if start < 0 or end < 0:
        raise SystemExit('R15 patch failed: existing account preparation block not found')
    immediate = r'''    private static void prepareExistingAccount(Activity activity, SharedPreferences prefs, JSONObject payload, JSONObject cfg, StorageChoice choice, SnapshotInfo snap, String username, String password) throws Exception {
        JSONObject account = findExistingAccountInSecurityBundle(payload, username);
        if (account == null || !account.optBoolean("active", true)) throw new Exception("Account non trovato o non attivo nel Dossier.");
        if (!R12Crypto.verifyAccountPassword(account, password)) throw new Exception("Credenziali dell'account non valide.");
        if (!account.optBoolean("mfaEnabled", false)) throw new Exception("Questo account non ha ancora un TOTP personale configurato. Configuralo prima dalla versione Windows.");
        String envelope = account.optString("mfaSecretEnvelope", "");
        if (envelope.isEmpty()) throw new Exception("Il TOTP di questo account non è ancora trasferibile tra dispositivi. Accedi una volta dalla versione Windows aggiornata e riprova.");
        String secret = R12Crypto.portableMfaUnprotect(envelope, password);
        activity.runOnUiThread(() -> {
            Toast.makeText(activity, "Account verificato", Toast.LENGTH_SHORT).show();
            showExistingTotpVerification(activity, prefs, payload, cfg, choice, snap, account, secret);
        });
    }

    private static JSONObject findExistingAccountInSecurityBundle(JSONObject payload, String username) {
        String wanted = R12Crypto.normalizeUsername(username);
        JSONObject security = payload.optJSONObject("securityBundle");
        JSONObject store = security == null ? null : security.optJSONObject("usersStore");
        JSONArray users = store == null ? null : store.optJSONArray("users");
        if (users == null) return null;
        for (int i = 0; i < users.length(); i++) {
            JSONObject user = users.optJSONObject(i);
            if (user == null) continue;
            String key = R12Crypto.normalizeUsername(user.optString("usernameKey", user.optString("username", "")));
            if (wanted.equals(key)) return new JSONObject(user.toString());
        }
        return null;
    }

'''
    s = s[:start] + immediate + s[end:]

    start = s.find('    private static void showExistingTotpVerification(Activity activity, SharedPreferences prefs, JSONObject payload, JSONObject cfg, StorageChoice choice, SnapshotInfo snap, JSONObject account, String secret, File partial) {')
    end = s.find('    private static void completeExistingFamilyConnection(Context context, SharedPreferences prefs, JSONObject payload, JSONObject cfg, StorageChoice choice, SnapshotInfo snap, JSONObject account, File partial) throws Exception {', start)
    if start < 0 or end < 0:
        raise SystemExit('R15 patch failed: TOTP/connection block not found')
    totp_and_progress = r'''    private static void showExistingTotpVerification(Activity activity, SharedPreferences prefs, JSONObject payload, JSONObject cfg, StorageChoice choice, SnapshotInfo snap, JSONObject account, String secret) {
        String username = account.optString("username", "Account");
        String issuer = "Dossier Sanitario Locale";
        String uri;
        try { uri = "otpauth://totp/" + URLEncoder.encode(issuer, "UTF-8") + ":" + URLEncoder.encode(username, "UTF-8") + "?secret=" + secret + "&issuer=" + URLEncoder.encode(issuer, "UTF-8") + "&algorithm=SHA1&digits=6&period=30"; }
        catch (Exception e) { uri = "otpauth://totp/Dossier?secret=" + secret; }
        final String otpUri = uri;
        LinearLayout box = dialogForm(activity);
        box.addView(body(activity, "Account riconosciuto: " + username + ". Usa il codice TOTP personale già configurato."));
        Button openAuth = button(activity, "Apri nell'app Authenticator");
        openAuth.setOnClickListener(v -> { try { activity.startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(otpUri))); } catch (ActivityNotFoundException e) { Toast.makeText(activity, "Nessuna app Authenticator ha accettato il collegamento. Usa la chiave manuale.", Toast.LENGTH_LONG).show(); } });
        box.addView(openAuth, top(8));
        EditText manual = field(activity, "Chiave manuale", groupSecret(secret)); manual.setFocusable(false); manual.setLongClickable(true); box.addView(manual);
        try { Bitmap qr = qrBitmap(otpUri, 520); ImageView image = new ImageView(activity); image.setImageBitmap(qr); image.setAdjustViewBounds(true); box.addView(image, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(activity, 260))); } catch (Exception ignored) {}
        EditText otp = field(activity, "Codice a 6 cifre", ""); otp.setInputType(android.text.InputType.TYPE_CLASS_NUMBER); box.addView(otp);
        new AlertDialog.Builder(activity).setTitle("Conferma TOTP personale").setView(box)
                .setNegativeButton("Annulla", null)
                .setPositiveButton("Verifica e importa", (d, w) -> {
                    if (!R12Crypto.verifyTotp(secret, clean(otp))) { Toast.makeText(activity, "Il codice TOTP non è valido", Toast.LENGTH_LONG).show(); return; }
                    startExistingImportProgress(activity, prefs, payload, cfg, choice, snap, account);
                }).show();
    }

    private static void startExistingImportProgress(Activity activity, SharedPreferences prefs, JSONObject payload, JSONObject cfg, StorageChoice choice, SnapshotInfo snap, JSONObject account) {
        ProgressDialog progress = new ProgressDialog(activity);
        progress.setTitle("Importazione del Dossier");
        progress.setProgressStyle(ProgressDialog.STYLE_HORIZONTAL);
        progress.setIndeterminate(false);
        progress.setMax(100);
        progress.setProgress(5);
        progress.setMessage("Preparazione archivio...");
        progress.setCancelable(false);
        progress.show();
        EXECUTOR.execute(() -> {
            File partial = null;
            try {
                JSONObject cloud = payload.getJSONObject("cloud");
                File root = ensureRoot(choice.root);
                SnapshotInfo readySnap = snap == null ? latestSnapshot(activity, cfg) : snap;
                if (readySnap == null) throw new Exception("Snapshot familiare non disponibile.");
                if (freeBytes(root) < requiredBytes(readySnap.size)) throw new Exception("Lo spazio disponibile non è più sufficiente per il Dossier.");
                partial = new File(root, "current_snapshot.dsl5.part");
                if (partial.exists()) partial.delete();
                final File partialRef = partial;
                activity.runOnUiThread(() -> { progress.setProgress(20); progress.setMessage("Download del Dossier dal cloud..."); });
                R12Rclone.copyFromRemote(activity, cloudRoot(cfg) + "/snapshots/" + readySnap.name, partialRef);
                if (readySnap.size > 0 && partialRef.length() != readySnap.size) { partialRef.delete(); throw new Exception("Il download del Dossier non ha la dimensione attesa."); }
                activity.runOnUiThread(() -> { progress.setProgress(65); progress.setMessage("Verifica integrità del Dossier..."); });
                byte[] recovery = R12Crypto.unb64Url(cloud.getString("recoveryKey"));
                findExistingAccount(partialRef, recovery, account.optString("username", ""));
                activity.runOnUiThread(() -> { progress.setProgress(78); progress.setMessage("Importazione dei dati..."); });
                completeExistingFamilyConnection(activity, prefs, payload, cfg, choice, readySnap, account, partialRef);
                activity.runOnUiThread(() -> {
                    progress.setProgress(100);
                    progress.setMessage("Completamento...");
                    progress.dismiss();
                    Toast.makeText(activity, "Dossier importato e dispositivo collegato", Toast.LENGTH_LONG).show();
                });
            } catch (Exception e) {
                if (partial != null && partial.exists()) partial.delete();
                String message = String.valueOf(e.getMessage());
                activity.runOnUiThread(() -> {
                    progress.dismiss();
                    new AlertDialog.Builder(activity).setTitle("Importazione non riuscita").setMessage(message == null || message.trim().isEmpty() ? "Operazione cloud non riuscita." : message).setPositiveButton("Chiudi", null).show();
                });
            }
        });
    }

'''
    s = s[:start] + totp_and_progress + s[end:]

    CLOUD.write_text(s, encoding='utf-8')


def patch_main():
    s = MAIN.read_text(encoding='utf-8')
    s = s.replace('Android R14 TEST', 'Android R15 TEST')
    s = s.replace('Aiuto R14', 'Aiuto R15')
    s = s.replace('R14: struttura presente', 'R15: struttura presente')
    s = s.replace('R14 mantiene lo stesso pacchetto Android', 'R15 mantiene lo stesso pacchetto Android')
    s = s.replace('Installala sopra la R13', 'Installala sopra la R14')
    MAIN.write_text(s, encoding='utf-8')


patch_cloud()
patch_main()
print('R15 immediate account verification, import progress and password eye patch applied')
