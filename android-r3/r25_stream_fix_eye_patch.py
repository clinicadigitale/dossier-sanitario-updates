from pathlib import Path

BASE = Path('android-r3/app/src/main/java/it/dossiersanitario/clinicadigitale/beta')
CLOUD = BASE / 'R12CloudManager.java'
MAIN = BASE / 'R6MainActivity.java'
GRADLE = Path('android-r3/app/build.gradle')


def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit(f'R25 patch failed: missing {label}')
    return text.replace(old, new, 1)


def replace_zip_reads_in_method(source, start_marker, end_marker, label):
    start = source.find(start_marker)
    end = source.find(end_marker, start)
    if start < 0 or end < 0:
        raise SystemExit(f'R25 patch failed: method block not found: {label}')
    block = source[start:end]
    if 'readAll(zip)' not in block:
        raise SystemExit(f'R25 patch failed: no closing ZIP reads found in {label}')
    block = block.replace('readAll(zip)', 'R25ZipEntryReader.readEntry(zip)')
    return source[:start] + block + source[end:]


def patch_cloud():
    s = CLOUD.read_text(encoding='utf-8')

    # readAll(InputStream) closes the stream passed to it. It must never be used
    # while a ZipInputStream still has more entries to process.
    s = replace_zip_reads_in_method(
        s,
        '    private static void importSnapshotWithProgress(',
        '    private static void finalizeExistingConnectionProgress(',
        'importSnapshotWithProgress',
    )
    s = replace_zip_reads_in_method(
        s,
        '    private static void importSnapshot(Context context, SharedPreferences prefs, JSONObject cfg, File snapshot, byte[] recovery) throws Exception {',
        '    private static void buildStandaloneSnapshot(',
        'importSnapshot',
    )

    CLOUD.write_text(s, encoding='utf-8')


def patch_main():
    s = MAIN.read_text(encoding='utf-8')

    old = r'''        card.addView(username);
        card.addView(password);
        card.addView(remember, matchWrapTop(8));
'''
    new = r'''        card.addView(username);
        LinearLayout passwordRow = new LinearLayout(this);
        passwordRow.setOrientation(LinearLayout.HORIZONTAL);
        LinearLayout.LayoutParams passwordParams = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f);
        passwordRow.addView(password, passwordParams);
        android.widget.ImageButton passwordEye = new android.widget.ImageButton(this);
        passwordEye.setImageResource(android.R.drawable.ic_menu_view);
        passwordEye.setContentDescription("Mostra password");
        passwordEye.setBackgroundColor(Color.TRANSPARENT);
        LinearLayout.LayoutParams eyeParams = new LinearLayout.LayoutParams(dp(48), dp(48));
        passwordRow.addView(passwordEye, eyeParams);
        final boolean[] passwordVisible = {false};
        passwordEye.setOnClickListener(v -> {
            passwordVisible[0] = !passwordVisible[0];
            int cursor = password.getSelectionStart();
            password.setInputType(android.text.InputType.TYPE_CLASS_TEXT |
                    (passwordVisible[0]
                            ? android.text.InputType.TYPE_TEXT_VARIATION_VISIBLE_PASSWORD
                            : android.text.InputType.TYPE_TEXT_VARIATION_PASSWORD));
            password.setSelection(Math.max(0, Math.min(cursor, password.length())));
            passwordEye.setContentDescription(passwordVisible[0] ? "Nascondi password" : "Mostra password");
        });
        card.addView(passwordRow);
        card.addView(remember, matchWrapTop(8));
'''
    s = replace_once(s, old, new, 'startup password visibility eye')

    s = s.replace('Android R24 TEST', 'Android R25 TEST')
    s = s.replace('Aiuto R24', 'Aiuto R25')
    s = s.replace('R24: struttura presente', 'R25: struttura presente')
    s = s.replace('R24 mantiene lo stesso pacchetto Android', 'R25 mantiene lo stesso pacchetto Android')
    s = s.replace('Installala sopra la R23', 'Installala sopra la R24')
    MAIN.write_text(s, encoding='utf-8')


def patch_version():
    g = GRADLE.read_text(encoding='utf-8')
    g = replace_once(g, 'versionCode 24', 'versionCode 25', 'versionCode')
    g = replace_once(g, "versionName '1.0.0-android-r24-test'", "versionName '1.0.0-android-r25-test'", 'versionName')
    GRADLE.write_text(g, encoding='utf-8')


patch_cloud()
patch_main()
patch_version()
print('R25 stream lifecycle fix and password eye patch applied')
