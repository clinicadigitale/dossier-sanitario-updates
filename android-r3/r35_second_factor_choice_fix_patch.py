from pathlib import Path

MAIN = Path('android-r3/app/src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java')
GRADLE = Path('android-r3/app/build.gradle')
s = MAIN.read_text(encoding='utf-8')


def replace_block(text, signature, replacement):
    start = text.find(signature)
    if start < 0:
        raise SystemExit(f'R35 patch failed: missing {signature}')
    brace = text.find('{', start)
    depth = 0
    end = -1
    for i in range(brace, len(text)):
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end < 0:
        raise SystemExit(f'R35 patch failed: unclosed {signature}')
    return text[:start] + replacement.rstrip() + '\n' + text[end:]


chooser = r'''    private void r34ShowSecondFactor(Bundle state, JSONObject account, String password) {
        String preferred = prefs.getString(SECOND_FACTOR_METHOD_KEY, SECOND_FACTOR_ASK);
        boolean biometric = R34BiometricAuth.available(this);
        boolean totp = account != null && !account.optString("mfaSecretEnvelope", "").trim().isEmpty();

        if (SECOND_FACTOR_BIOMETRIC.equals(preferred) && biometric) {
            r34AuthenticateBiometricForAccount(state, account, password);
            return;
        }
        if (SECOND_FACTOR_TOTP.equals(preferred) && totp) {
            r34ShowTotpForAccount(state, account, password);
            return;
        }
        if (!biometric && totp) {
            r34ShowTotpForAccount(state, account, password);
            return;
        }
        if (biometric && !totp) {
            r34AuthenticateBiometricForAccount(state, account, password);
            return;
        }
        if (!biometric && !totp) {
            new AlertDialog.Builder(this)
                    .setTitle("Seconda verifica non disponibile")
                    .setMessage("Su questo dispositivo non è disponibile alcun metodo di seconda verifica. Configura la biometria del telefono oppure usa un account con TOTP disponibile.")
                    .setNegativeButton("Esci", (d,w)->finishAndRemoveTask())
                    .setCancelable(false)
                    .show();
            return;
        }

        // R34 used setMessage together with setItems. On Android's AlertDialog the
        // message panel can replace the list panel, leaving only the Exit button.
        // R35 uses real dialog buttons so both methods remain visible on device.
        AlertDialog.Builder builder = new AlertDialog.Builder(this)
                .setTitle("Scegli il metodo di verifica")
                .setMessage("Scegli come completare l'accesso al Dossier.")
                .setNegativeButton("Esci", (d,w)->finishAndRemoveTask())
                .setCancelable(false);

        if (biometric) {
            builder.setPositiveButton("Biometria", (d,w) ->
                    r34AuthenticateBiometricForAccount(state, account, password));
        }
        if (totp) {
            builder.setNeutralButton("Codice TOTP", (d,w) ->
                    r34ShowTotpForAccount(state, account, password));
        }
        builder.show();
    }'''

s = replace_block(s, '    private void r34ShowSecondFactor(Bundle state, JSONObject account, String password) {', chooser)

s = s.replace('Android R34 TEST COMPLETO', 'Android R35 TEST COMPLETO')
s = s.replace('Aiuto R34', 'Aiuto R35')
MAIN.write_text(s, encoding='utf-8')

g = GRADLE.read_text(encoding='utf-8')
if 'versionCode 34' not in g or "versionName '1.0.0-android-r34-sync-biometrics-contacts-layout-test'" not in g:
    raise SystemExit('R35 patch failed: R34 version identity missing')
g = g.replace('versionCode 34', 'versionCode 35', 1)
g = g.replace("versionName '1.0.0-android-r34-sync-biometrics-contacts-layout-test'", "versionName '1.0.0-android-r35-second-factor-choice-fix-test'", 1)
GRADLE.write_text(g, encoding='utf-8')

print('R35 second-factor chooser visibility fix applied')
