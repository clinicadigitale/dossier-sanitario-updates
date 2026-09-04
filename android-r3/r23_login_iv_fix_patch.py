from pathlib import Path

BASE = Path('android-r3/app/src/main/java/it/dossiersanitario/clinicadigitale/beta')
MAIN = BASE / 'R6MainActivity.java'
CLOUD = BASE / 'R12CloudManager.java'
CRYPTO = BASE / 'R12Crypto.java'
GRADLE = Path('android-r3/app/build.gradle')


def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit(f'R23 patch failed: missing {label}')
    return text.replace(old, new, 1)


def patch_crypto():
    s = CRYPTO.read_text(encoding='utf-8')
    old = r'''    public static String protectSecret(Context context, String plain) throws Exception {
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
'''
    new = r'''    public static String protectSecret(Context context, String plain) throws Exception {
        SecretKey key = localSecretKey();
        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        // AndroidKeyStore con randomizedEncryptionRequired usa esclusivamente
        // un IV generato dal provider. Non fornire mai un IV in ENCRYPT_MODE.
        cipher.init(Cipher.ENCRYPT_MODE, key);
        byte[] iv = cipher.getIV();
        if (iv == null || iv.length != 12) throw new Exception("IV segreto locale non valido");
        byte[] encrypted = cipher.doFinal(String.valueOf(plain).getBytes(StandardCharsets.UTF_8));
        ByteArrayOutputStream out = new ByteArrayOutputStream(iv.length + encrypted.length);
        out.write(iv);
        out.write(encrypted);
        return b64(out.toByteArray());
    }
'''
    s = replace_once(s, old, new, 'R12Crypto AndroidKeyStore IV generation')
    CRYPTO.write_text(s, encoding='utf-8')


def patch_cloud():
    s = CLOUD.read_text(encoding='utf-8')

    start = s.find('    private static void prepareExistingAccount(Activity activity, SharedPreferences prefs, JSONObject payload, JSONObject cfg, StorageChoice choice, SnapshotInfo snap, String username, String password) throws Exception {')
    end = s.find('    private static JSONObject findExistingAccountInSecurityBundle(JSONObject payload, String username) {', start)
    if start < 0 or end < 0:
        raise SystemExit('R23 patch failed: prepareExistingAccount block not found')

    replacement = r'''    private static void prepareExistingAccount(Activity activity, SharedPreferences prefs, JSONObject payload, JSONObject cfg, StorageChoice choice, SnapshotInfo snap, String username, String password) throws Exception {
        JSONObject account = findExistingAccountInSecurityBundle(payload, username);
        if (account == null || !account.optBoolean("active", true)) throw new Exception("Account non trovato o non attivo nel Dossier.");
        if (!R12Crypto.verifyAccountPassword(account, password)) throw new Exception("Credenziali dell'account non valide.");

        // Prima sincronizzazione: la chiave Dossier e le credenziali sono già
        // sufficienti. Il TOTP diventa un fattore di accesso soltanto dopo che
        // il Dossier è stato importato e l'associazione è attiva.
        activity.runOnUiThread(() -> {
            try {
                persistExistingImportCheckpoint(activity, prefs, payload, cfg, choice, snap, account);
                Toast.makeText(activity, "Account verificato. Avvio importazione del Dossier.", Toast.LENGTH_SHORT).show();
                safeStartExistingImportProgress(activity, prefs, payload, cfg, choice, snap, account);
            } catch (Exception e) {
                Toast.makeText(activity, "Non è stato possibile memorizzare il collegamento del dispositivo.", Toast.LENGTH_LONG).show();
            }
        });
    }

'''
    s = s[:start] + replacement + s[end:]

    success_old = '                    Toast.makeText(activity, "Dossier importato e dispositivo collegato", Toast.LENGTH_LONG).show();\n'
    success_new = '                    Toast.makeText(activity, "Dossier importato e dispositivo collegato", Toast.LENGTH_LONG).show();\n                    activity.recreate();\n'
    s = replace_once(s, success_old, success_new, 'recreate after successful import')

    close_old = r'''                            .setTitle("Importazione interrotta")
                            .setMessage((message == null || message.trim().isEmpty() ? "Operazione cloud non riuscita." : message) + "\n\nIl dispositivo resta autenticato. Puoi riprendere l'importazione senza reinserire chiave, account o TOTP.")
                            .setPositiveButton("Chiudi", null)
                            .show();
'''
    close_new = r'''                            .setTitle("Importazione interrotta")
                            .setMessage((message == null || message.trim().isEmpty() ? "Operazione cloud non riuscita." : message) + "\n\nIl collegamento con il Dossier resta memorizzato. Alla riapertura saranno richieste solo le credenziali dell'account; il TOTP non è richiesto finché il primo Dossier non è stato sincronizzato.")
                            .setPositiveButton("Chiudi", (d, w) -> activity.recreate())
                            .show();
'''
    s = replace_once(s, close_old, close_new, 'resume message and login recreation')

    CLOUD.write_text(s, encoding='utf-8')


def patch_main():
    s = MAIN.read_text(encoding='utf-8')

    if 'import android.widget.CheckBox;' not in s:
        s = replace_once(s, 'import android.widget.Button;\n', 'import android.widget.Button;\nimport android.widget.CheckBox;\n', 'CheckBox import')
    if 'import org.json.JSONObject;' not in s:
        s = replace_once(s, 'import java.io.File;\n', 'import org.json.JSONObject;\n\nimport java.io.File;\n', 'JSONObject import')

    s = replace_once(
        s,
        '    private static final String PREFS = "clinica_android_beta";\n',
        '    private static final String PREFS = "clinica_android_beta";\n'
        '    private static final String ACCOUNT_PREF_KEY = "r12_account_json";\n'
        '    private static final String CONFIG_PREF_KEY = "r12_cloud_config_json";\n'
        '    private static final String REMEMBER_USER_KEY = "r23_login_user";\n'
        '    private static final String REMEMBER_PASSWORD_KEY = "r23_login_password_secure";\n',
        'login preference constants'
    )

    s = replace_once(
        s,
        '    private long lastPanoramicaBackMs = 0L;\n',
        '    private long lastPanoramicaBackMs = 0L;\n    private boolean sessionAuthenticated = false;\n',
        'session auth state'
    )

    old_oncreate = r'''    @Override protected void onCreate(Bundle state) {
        super.onCreate(state);
        prefs = getSharedPreferences(PREFS, MODE_PRIVATE);
        cleanCameraTemp();

        Window w = getWindow();
        w.setStatusBarColor(GREEN_DARK);
        w.setNavigationBarColor(Color.WHITE);
        if (Build.VERSION.SDK_INT >= 23) w.getDecorView().setSystemUiVisibility(0);

        setContentView(buildUi());
        String initial = state == null ? "Panoramica" : state.getString("current_section", "Panoramica");
        renderSection(initial);
    }
'''
    new_oncreate = r'''    @Override protected void onCreate(Bundle state) {
        super.onCreate(state);
        prefs = getSharedPreferences(PREFS, MODE_PRIVATE);
        cleanCameraTemp();

        Window w = getWindow();
        w.setStatusBarColor(GREEN_DARK);
        w.setNavigationBarColor(Color.WHITE);
        if (Build.VERSION.SDK_INT >= 23) w.getDecorView().setSystemUiVisibility(0);

        showStartupGate(state);
    }
'''
    s = replace_once(s, old_oncreate, new_oncreate, 'startup gate onCreate')

    marker = '    private View buildUi() {\n'
    if marker not in s:
        raise SystemExit('R23 patch failed: buildUi marker not found')

    auth_methods = r'''    private void showStartupGate(Bundle state) {
        sessionAuthenticated = false;
        JSONObject account = localAccount();
        if (account == null) {
            showPairingOnlyScreen();
            return;
        }
        showLoginScreen(state, account);
    }

    private JSONObject localAccount() {
        try {
            String raw = prefs.getString(ACCOUNT_PREF_KEY, "");
            return raw == null || raw.trim().isEmpty() ? null : new JSONObject(raw);
        } catch (Exception e) {
            return null;
        }
    }

    private JSONObject localConfig() {
        try {
            String raw = prefs.getString(CONFIG_PREF_KEY, "");
            return raw == null || raw.trim().isEmpty() ? new JSONObject() : new JSONObject(raw);
        } catch (Exception e) {
            return new JSONObject();
        }
    }

    private void showPairingOnlyScreen() {
        LinearLayout page = securePage("Collega il Dossier", "Prima di accedere ai dati sanitari collega questo dispositivo al Dossier esistente.");
        LinearLayout cloud = new LinearLayout(this);
        cloud.setOrientation(LinearLayout.VERTICAL);
        cloud.setPadding(dp(16), dp(4), dp(16), dp(24));
        page.addView(cloud, matchWrap());
        R12CloudManager.renderCloudPanel(this, cloud, prefs);
        setContentView(wrapSecurePage(page));
    }

    private void showLoginScreen(Bundle state, JSONObject account) {
        LinearLayout page = securePage("Accesso al Dossier", "Inserisci le credenziali dell'account. Il Dossier non viene aperto automaticamente all'avvio.");
        LinearLayout card = card();

        String accountUser = account.optString("username", account.optString("usernameKey", ""));
        String rememberedUser = prefs.getString(REMEMBER_USER_KEY, "");
        String rememberedPassword = "";
        String protectedPassword = prefs.getString(REMEMBER_PASSWORD_KEY, "");
        if (protectedPassword != null && !protectedPassword.trim().isEmpty()) {
            try { rememberedPassword = R12Crypto.unprotectSecret(this, protectedPassword); }
            catch (Exception e) { prefs.edit().remove(REMEMBER_PASSWORD_KEY).apply(); }
        }

        EditText username = field("Nome utente", rememberedUser.trim().isEmpty() ? accountUser : rememberedUser);
        EditText password = field("Password", rememberedPassword);
        password.setInputType(android.text.InputType.TYPE_CLASS_TEXT | android.text.InputType.TYPE_TEXT_VARIATION_PASSWORD);
        CheckBox remember = new CheckBox(this);
        remember.setText("Ricorda le credenziali su questo dispositivo");
        remember.setChecked(!rememberedPassword.isEmpty());
        remember.setTextColor(TEXT);

        card.addView(username);
        card.addView(password);
        card.addView(remember, matchWrapTop(8));

        Button login = button("Accedi");
        login.setOnClickListener(v -> attemptStartupLogin(state, account, clean(username), password.getText().toString(), remember.isChecked()));
        card.addView(login, matchWrapTop(12));
        page.addView(card, matchWrapBottom(14));
        setContentView(wrapSecurePage(page));
    }

    private void attemptStartupLogin(Bundle state, JSONObject account, String username, String password, boolean remember) {
        try {
            String expectedUser = account.optString("username", account.optString("usernameKey", ""));
            if (!R12Crypto.normalizeUsername(expectedUser).equals(R12Crypto.normalizeUsername(username))
                    || !R12Crypto.verifyAccountPassword(account, password)) {
                Toast.makeText(this, "Credenziali non valide", Toast.LENGTH_LONG).show();
                return;
            }

            if (remember) {
                try {
                    String protectedPassword = R12Crypto.protectSecret(this, password);
                    prefs.edit().putString(REMEMBER_USER_KEY, username).putString(REMEMBER_PASSWORD_KEY, protectedPassword).apply();
                } catch (Exception e) {
                    prefs.edit().putString(REMEMBER_USER_KEY, username).remove(REMEMBER_PASSWORD_KEY).apply();
                    Toast.makeText(this, "Nome utente memorizzato, password non memorizzata", Toast.LENGTH_LONG).show();
                }
            } else {
                prefs.edit().remove(REMEMBER_USER_KEY).remove(REMEMBER_PASSWORD_KEY).apply();
            }

            JSONObject cfg = localConfig();
            boolean dossierSynchronized = "active".equals(cfg.optString("associationStatus", ""));
            if (!dossierSynchronized) {
                sessionAuthenticated = true;
                showPendingImportScreen();
                return;
            }

            if (account.optBoolean("mfaEnabled", false)) {
                String envelope = account.optString("mfaSecretEnvelope", "");
                if (envelope.trim().isEmpty()) {
                    Toast.makeText(this, "TOTP configurato ma non disponibile su questo dispositivo", Toast.LENGTH_LONG).show();
                    return;
                }
                String secret = R12Crypto.portableMfaUnprotect(envelope, password);
                showStartupTotp(state, secret);
                return;
            }

            sessionAuthenticated = true;
            showMainUi(state);
        } catch (Exception e) {
            Toast.makeText(this, "Accesso non riuscito", Toast.LENGTH_LONG).show();
        }
    }

    private void showStartupTotp(Bundle state, String secret) {
        EditText otp = field("Codice TOTP a 6 cifre", "");
        otp.setInputType(android.text.InputType.TYPE_CLASS_NUMBER);
        new AlertDialog.Builder(this)
                .setTitle("Conferma TOTP")
                .setMessage("Il Dossier è già sincronizzato. Inserisci il codice TOTP personale per completare l'accesso.")
                .setView(otp)
                .setCancelable(false)
                .setNegativeButton("Esci", (d, w) -> finishAndRemoveTask())
                .setPositiveButton("Accedi", (d, w) -> {
                    if (!R12Crypto.verifyTotp(secret, clean(otp))) {
                        Toast.makeText(this, "Il codice TOTP non è valido", Toast.LENGTH_LONG).show();
                        showStartupTotp(state, secret);
                        return;
                    }
                    sessionAuthenticated = true;
                    showMainUi(state);
                })
                .show();
    }

    private void showPendingImportScreen() {
        LinearLayout page = securePage("Dossier da sincronizzare", "Le credenziali sono state verificate. Il TOTP non è richiesto finché la prima sincronizzazione del Dossier non è completata.");
        LinearLayout cloud = new LinearLayout(this);
        cloud.setOrientation(LinearLayout.VERTICAL);
        cloud.setPadding(dp(16), dp(4), dp(16), dp(24));
        page.addView(cloud, matchWrap());
        R12CloudManager.renderCloudPanel(this, cloud, prefs);
        Button lock = button("Blocca e torna al login");
        lock.setOnClickListener(v -> showStartupGate(null));
        cloud.addView(lock, matchWrapTop(10));
        setContentView(wrapSecurePage(page));
    }

    private void showMainUi(Bundle state) {
        if (!sessionAuthenticated) {
            showStartupGate(state);
            return;
        }
        setContentView(buildUi());
        String initial = state == null ? "Panoramica" : state.getString("current_section", "Panoramica");
        renderSection(initial);
    }

    private LinearLayout securePage(String titleText, String subtitleText) {
        LinearLayout page = new LinearLayout(this);
        page.setOrientation(LinearLayout.VERTICAL);
        page.setPadding(dp(16), dp(24), dp(16), dp(24));
        page.setBackgroundColor(PAGE);
        ImageView icon = new ImageView(this);
        icon.setImageResource(R.drawable.dossier_sanitario);
        icon.setScaleType(ImageView.ScaleType.FIT_CENTER);
        page.addView(icon, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(110)));
        TextView title = text(titleText, 24, TEXT, true);
        title.setGravity(Gravity.CENTER);
        page.addView(title, matchWrapTop(8));
        TextView subtitle = text(subtitleText, 14, MUTED, false);
        subtitle.setGravity(Gravity.CENTER);
        page.addView(subtitle, matchWrapTop(6));
        return page;
    }

    private View wrapSecurePage(LinearLayout page) {
        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        scroll.setBackgroundColor(PAGE);
        scroll.addView(page, new ScrollView.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        return scroll;
    }

'''
    s = s.replace(marker, auth_methods + marker, 1)

    logout_start = s.find('    private void renderLogout() {')
    logout_end = s.find('    private void renderStructuralSection(String section) {', logout_start)
    if logout_start < 0 or logout_end < 0:
        raise SystemExit('R23 patch failed: logout block not found')
    logout = r'''    private void renderLogout() {
        LinearLayout c = card();
        c.addView(sectionHeader("Logout"));
        c.addView(text("Blocca il Dossier e torna alla schermata di accesso. Il collegamento al Dossier familiare non viene eliminato.", 14, MUTED, false));
        Button lock = button("Blocca Dossier");
        lock.setOnClickListener(v -> {
            sessionAuthenticated = false;
            navigationHistory.clear();
            showStartupGate(null);
        });
        c.addView(lock, matchWrapTop(10));
        content.addView(c, matchWrapBottom(14));
    }

'''
    s = s[:logout_start] + logout + s[logout_end:]

    s = s.replace('Android R22 TEST', 'Android R23 TEST')
    s = s.replace('Aiuto R22', 'Aiuto R23')
    s = s.replace('R22: struttura presente', 'R23: struttura presente')
    s = s.replace('R22 mantiene lo stesso pacchetto Android', 'R23 mantiene lo stesso pacchetto Android')
    s = s.replace('Installala sopra la R21', 'Installala sopra la R22')
    MAIN.write_text(s, encoding='utf-8')


def patch_version():
    g = GRADLE.read_text(encoding='utf-8')
    g = replace_once(g, 'versionCode 22', 'versionCode 23', 'versionCode')
    g = replace_once(g, "versionName '1.0.0-android-r22-test'", "versionName '1.0.0-android-r23-test'", 'versionName')
    GRADLE.write_text(g, encoding='utf-8')


patch_crypto()
patch_cloud()
patch_main()
patch_version()
print('R23 startup login, pre-sync no-TOTP and AndroidKeyStore IV fix applied')
