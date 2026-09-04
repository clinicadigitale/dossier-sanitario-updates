from pathlib import Path

BASE = Path('android-r3/app/src/main/java/it/dossiersanitario/clinicadigitale/beta')
MAIN = BASE / 'R6MainActivity.java'
GRADLE = Path('android-r3/app/build.gradle')


def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit(f'R28 patch failed: missing {label}')
    return text.replace(old, new, 1)

s = MAIN.read_text(encoding='utf-8')

# R27 regression: exact Windows reconstruction was executed synchronously in onCreate,
# before the login screen. A populated archive can therefore block Android's UI thread
# long enough for the app to look as if it never opened. Startup must remain immediate.
s = replace_once(
    s,
    '        cleanCameraTemp();\n        R12CloudManager.bootstrapR27ExactIfNeeded(this, prefs);\n        loadR26ImportedUiSettings();\n',
    '        cleanCameraTemp();\n        loadR26ImportedUiSettings();\n',
    'remove synchronous Windows bootstrap from onCreate'
)

# Route the two authenticated-open paths (password-only and successful TOTP)
# through one post-login asynchronous migration gate.
needle_plain = '            sessionAuthenticated = true;\n            showMainUi(state);\n'
if s.count(needle_plain) < 1:
    raise SystemExit('R28 patch failed: password login open path missing')
s = s.replace(needle_plain, '            openAuthenticatedDossierR28(state);\n', 1)

needle_totp = '                    sessionAuthenticated = true;\n                    showMainUi(state);\n'
if needle_totp not in s:
    raise SystemExit('R28 patch failed: TOTP open path missing')
s = s.replace(needle_totp, '                    openAuthenticatedDossierR28(state);\n', 1)

marker = '    private void showMainUi(Bundle state) {'
if marker not in s:
    raise SystemExit('R28 patch failed: showMainUi marker missing')

methods = r'''    private void openAuthenticatedDossierR28(Bundle state) {
        sessionAuthenticated = true;

        // Fresh R27/R28 imports already contain the exact Windows state.
        // Standalone/non-cloud dossiers also have nothing to migrate here.
        if (R27ExactWindows.profiles(prefs).length() > 0 || !R12CloudManager.configured(prefs)) {
            loadR26ImportedUiSettings();
            showMainUi(state);
            return;
        }

        showR28WindowsMigrationScreen();
        dataExecutor.execute(() -> {
            final boolean imported = R12CloudManager.bootstrapR27ExactIfNeeded(this, prefs);
            runOnUiThread(() -> {
                if (isFinishing() || isDestroyed() || !sessionAuthenticated) return;
                if (!imported) {
                    showR28WindowsMigrationFailure(state);
                    return;
                }
                loadR26ImportedUiSettings();
                getWindow().setStatusBarColor(GREEN_DARK);
                showMainUi(state);
            });
        });
    }

    private void showR28WindowsMigrationScreen() {
        LinearLayout page = securePage(
                "Preparazione del Dossier",
                "Sto importando sul dispositivo i dati e le impostazioni già sincronizzati da Windows. L'accesso resta bloccato finché il passaggio non è completato.");
        LinearLayout card = card();
        card.addView(text("Importazione di profili, documenti, tessera sanitaria, grafici, preferenze e colori Windows…", 14, TEXT, true));
        card.addView(text("Questa operazione viene eseguita una sola volta per l'aggiornamento della struttura Android.", 13, MUTED, false));
        page.addView(card, matchWrapBottom(14));
        setContentView(wrapSecurePage(page));
    }

    private void showR28WindowsMigrationFailure(Bundle state) {
        LinearLayout page = securePage(
                "Importazione Windows non completata",
                "Il Dossier resta protetto e non viene aperto con dati parziali.");
        LinearLayout card = card();
        card.addView(text("Non è stato possibile ricostruire sul dispositivo la copia completa già sincronizzata da Windows.", 14, TEXT, true));
        Button retry = button("Riprova importazione");
        retry.setOnClickListener(v -> openAuthenticatedDossierR28(state));
        card.addView(retry, matchWrapTop(12));
        Button lock = button("Blocca e torna al login");
        lock.setOnClickListener(v -> showStartupGate(null));
        card.addView(lock, matchWrapTop(8));
        page.addView(card, matchWrapBottom(14));
        setContentView(wrapSecurePage(page));
    }

'''
s = s.replace(marker, methods + marker, 1)

# Visible test label only. No unrelated UI/feature changes.
s = s.replace('Android R27 TEST COMPLETO', 'Android R28 TEST COMPLETO')
s = s.replace('Aiuto R27', 'Aiuto R28')
s = s.replace('R27: sezione completa collegata al backup Windows', 'R28: sezione completa collegata al backup Windows')
s = s.replace('R27 mantiene lo stesso pacchetto Android', 'R28 mantiene lo stesso pacchetto Android')
s = s.replace('Installala sopra la R26', 'Installala sopra la R27')
MAIN.write_text(s, encoding='utf-8')

g = GRADLE.read_text(encoding='utf-8')
g = replace_once(g, 'versionCode 27', 'versionCode 28', 'versionCode')
g = replace_once(g, "versionName '1.0.0-android-r27-complete-test'", "versionName '1.0.0-android-r28-startup-async-test'", 'versionName')
GRADLE.write_text(g, encoding='utf-8')
print('R28 asynchronous startup migration patch applied')
