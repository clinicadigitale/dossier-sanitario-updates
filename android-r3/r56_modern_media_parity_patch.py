from pathlib import Path
import re

base = Path('android-r3/app/src/main/java/it/dossiersanitario/clinicadigitale/beta')

# 1) Extend the Windows snapshot reader with the new imaging metadata only.
# Heavy media are deliberately NOT extracted automatically on Android.
r27p = base / 'R27ExactWindows.java'
r27 = r27p.read_text(encoding='utf-8')
anchor = '                putArray(editor, profileId, "calendarSuggestions", readArray(zip, entries.get(folder + "richiami_calendario.json")));\n'
if anchor not in r27:
    raise SystemExit('R56 R27 metadata import anchor not found')
insert = anchor + '                putArray(editor, profileId, "dicomStudies", readArray(zip, entries.get(folder + "dicom_studies.json")));\n' + \
         '                putArray(editor, profileId, "mediaAttachments", readArray(zip, entries.get(folder + "immagini_associate.json")));\n'
r27 = r27.replace(anchor, insert, 1)
anchor2 = '    static JSONArray calendarSuggestions(SharedPreferences prefs) { return data(prefs, "calendarSuggestions"); }\n'
if anchor2 not in r27:
    raise SystemExit('R56 R27 accessor anchor not found')
r27 = r27.replace(anchor2, anchor2 + '    static JSONArray dicomStudies(SharedPreferences prefs) { return data(prefs, "dicomStudies"); }\n    static JSONArray mediaAttachments(SharedPreferences prefs) { return data(prefs, "mediaAttachments"); }\n', 1)
r27p.write_text(r27, encoding='utf-8')

# 2) Modernise shared Android chrome without altering clinical engines.
mainp = base / 'R6MainActivity.java'
main = mainp.read_text(encoding='utf-8')

# Palette is still profile/theme driven by later patches; these are safe visual fallbacks.
main = main.replace('private static final int GREEN = Color.rgb(23, 138, 114);', 'private static final int GREEN = Color.rgb(15, 118, 110);')
main = main.replace('private static final int GREEN_DARK = Color.rgb(19, 110, 93);', 'private static final int GREEN_DARK = Color.rgb(17, 94, 89);')
main = main.replace('private static final int TEXT = Color.rgb(32, 48, 45);', 'private static final int TEXT = Color.rgb(24, 38, 36);')
main = main.replace('private static final int PAGE = Color.rgb(246, 249, 248);', 'private static final int PAGE = Color.rgb(247, 249, 249);')
main = main.replace('private static final int BORDER = Color.rgb(224, 232, 229);', 'private static final int BORDER = Color.rgb(221, 229, 227);')

# Add the imaging/media entry without removing any existing section.
if '"Imaging e media"' not in main:
    replaced = False
    for old in ['"Monitoraggio", "Preferenze"', '"Monitoraggio","Preferenze"']:
        if old in main:
            main = main.replace(old, old.replace('"Preferenze"', '"Imaging e media", "Preferenze"'), 1)
            replaced = True
            break
    if not replaced:
        # Later R53/R54 builds may have reformatted the array.
        m = re.search(r'(private static final String\[\] SECTIONS\s*=\s*\{.*?)("Preferenze")', main, re.S)
        if not m:
            raise SystemExit('R56 SECTIONS anchor not found')
        main = main[:m.start(2)] + '"Imaging e media", ' + main[m.start(2):]

# Route and subtitle.
if 'case "Imaging e media":' not in main:
    route_anchor = '            case "Backup": renderBackup(); break;'
    if route_anchor not in main:
        raise SystemExit('R56 render route anchor not found')
    main = main.replace(route_anchor, '            case "Imaging e media": renderImagingMedia(); break;\n' + route_anchor, 1)

subtitle_anchor = '            case "Backup": return "Protezione e continuità dei dati tra dispositivi e versioni.";'
if subtitle_anchor in main and 'case "Imaging e media": return' not in main:
    main = main.replace(subtitle_anchor, '            case "Imaging e media": return "Studi DICOM, immagini associate e disponibilità offline.";\n' + subtitle_anchor, 1)

# Shared modern proportions. Only presentation tokens are changed.
replacements = [
    ('header.setPadding(dp(10), dp(5), dp(10), dp(5));', 'header.setPadding(dp(14), dp(8), dp(14), dp(8));'),
    ('new LinearLayout.LayoutParams(dp(92), dp(92))', 'new LinearLayout.LayoutParams(dp(56), dp(56))'),
    ('text("Dossier Sanitario", 24, Color.WHITE, true)', 'text("Clinica Digitale", 20, Color.WHITE, true)'),
    ('new LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, dp(46))', 'new LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, dp(42))'),
    ('profileBar.setPadding(dp(16), dp(9), dp(16), dp(9));', 'profileBar.setPadding(dp(16), dp(8), dp(16), dp(8));'),
    ('topbar.setPadding(dp(16), dp(13), dp(16), dp(12));', 'topbar.setPadding(dp(16), dp(15), dp(16), dp(10));'),
    ('viewTitle = text("Panoramica", 24, TEXT, true);', 'viewTitle = text("Panoramica", 23, TEXT, true);'),
    ('content.setPadding(dp(16), dp(4), dp(16), dp(28));', 'content.setPadding(dp(16), dp(8), dp(16), dp(32));'),
    ('c.setPadding(dp(15), dp(15), dp(15), dp(15));', 'c.setPadding(dp(16), dp(16), dp(16), dp(16));'),
    ('c.setBackground(roundRect(Color.WHITE, BORDER, 14));', 'c.setBackground(roundRect(Color.WHITE, BORDER, 18));'),
    ('c.setElevation(dp(1));', 'c.setElevation(dp(2));'),
    ('b.setBackground(roundRect(GREEN, GREEN_DARK, 10));', 'b.setBackground(roundRect(GREEN, GREEN_DARK, 13));'),
    ('b.setBackground(roundRect(Color.WHITE, Color.rgb(195, 214, 208), 10));', 'b.setBackground(roundRect(Color.WHITE, Color.rgb(205, 219, 216), 13));'),
]
for old,new in replacements:
    main = main.replace(old,new)

# Add the imaging page as a surgical UI entry point.
if 'private void renderImagingMedia()' not in main:
    insert_at = main.find('    private void renderBackup()')
    if insert_at < 0:
        insert_at = main.find('    private void renderAiuto()')
    if insert_at < 0:
        raise SystemExit('R56 imaging method insertion anchor not found')
    method = '''    private void renderImagingMedia() {\n        LinearLayout c = card();\n        c.addView(sectionHeader("Imaging e media"));\n        c.addView(text("Consulta gli studi DICOM e le immagini collegate ai referti senza riempire automaticamente la memoria del telefono.", 13, MUTED, false));\n        Button open = button("Apri Imaging e media");\n        open.setOnClickListener(v -> startActivity(new Intent(this, R56MediaActivity.class)));\n        c.addView(open, matchWrapTop(10));\n        content.addView(c, matchWrapBottom(14));\n    }\n\n'''
    main = main[:insert_at] + method + main[insert_at:]
mainp.write_text(main, encoding='utf-8')

# 3) Apply the same compact/modern visual language to R53 special tools.
specialp = base / 'R53SpecialToolsActivity.java'
special = specialp.read_text(encoding='utf-8')
special_replacements = [
    ('header.setPadding(dp(10),dp(5),dp(10),dp(5));', 'header.setPadding(dp(14),dp(8),dp(14),dp(8));'),
    ('new LinearLayout.LayoutParams(dp(92),dp(92))', 'new LinearLayout.LayoutParams(dp(56),dp(56))'),
    ('text("Dossier Sanitario",24,Color.WHITE,true)', 'text("Clinica Digitale",20,Color.WHITE,true)'),
    ('new LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT,dp(46))', 'new LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT,dp(42))'),
    ('profileBar.setPadding(dp(16),dp(9),dp(16),dp(9));', 'profileBar.setPadding(dp(16),dp(8),dp(16),dp(8));'),
    ('topbar.setPadding(dp(16),dp(13),dp(16),dp(12));', 'topbar.setPadding(dp(16),dp(15),dp(16),dp(10));'),
    ('TextView pageTitle=text(title,24,TEXT,true);', 'TextView pageTitle=text(title,23,TEXT,true);'),
    ('content.setPadding(dp(16),dp(4),dp(16),dp(28));', 'content.setPadding(dp(16),dp(8),dp(16),dp(32));'),
]
for old,new in special_replacements:
    special = special.replace(old,new)
# Shared card/button helper styles, when present in generated R53 source.
special = special.replace('roundRect(Color.WHITE,BORDER,14)', 'roundRect(Color.WHITE,BORDER,18)')
special = special.replace('roundRect(GREEN,GREEN_DARK,10)', 'roundRect(GREEN,GREEN_DARK,13)')
special = special.replace('roundRect(Color.WHITE,Color.rgb(195,214,208),10)', 'roundRect(Color.WHITE,Color.rgb(205,219,216),13)')
specialp.write_text(special, encoding='utf-8')

# 4) Manifest: add only the new internal media screen.
manifestp = Path('android-r3/app/src/main/AndroidManifest.xml')
manifest = manifestp.read_text(encoding='utf-8')
if '.R56MediaActivity' not in manifest:
    activity = '''        <activity\n            android:name=".R56MediaActivity"\n            android:exported="false"\n            android:screenOrientation="unspecified" />\n\n'''
    anchor = '        <activity\n            android:name=".R6MainActivity"'
    if anchor not in manifest:
        raise SystemExit('R56 manifest anchor not found')
    manifest = manifest.replace(anchor, activity + anchor, 1)
manifestp.write_text(manifest, encoding='utf-8')

# 5) Version identity.
gradlep = Path('android-r3/app/build.gradle')
gradle = gradlep.read_text(encoding='utf-8')
gradle = re.sub(r'versionCode\s+55\b', 'versionCode 56', gradle, count=1)
gradle = gradle.replace("versionName '1.0.0-android-r55-special-tools-layout-order-cleanup-test'", "versionName '1.0.0-android-r56-modern-media-parity-test'")
if 'versionCode 56' not in gradle:
    raise SystemExit('R56 versionCode bump failed')
gradlep.write_text(gradle, encoding='utf-8')

# Align inherited tests with the deliberate version bump only.
for p in Path('android-r3/app/src/test').rglob('*.java'):
    s=p.read_text(encoding='utf-8')
    ns=s.replace('versionCode 55','versionCode 56').replace('versionCode = 55','versionCode = 56')
    ns=ns.replace('1.0.0-android-r55-special-tools-layout-order-cleanup-test','1.0.0-android-r56-modern-media-parity-test')
    if ns!=s:p.write_text(ns,encoding='utf-8')

print('R56 modern media parity patch applied')
