from pathlib import Path
import re

BASE = Path('android-r3/app/src/main/java/it/dossiersanitario/clinicadigitale/beta')
TEST = Path('android-r3/app/src/test/java/it/dossiersanitario/clinicadigitale/beta')
MAIN = BASE / 'R6MainActivity.java'
MEDIA = BASE / 'R56MediaActivity.java'
GRADLE = Path('android-r3/app/build.gradle')


def require(text, needle, label):
    if needle not in text:
        raise SystemExit('R58 missing ' + label)


main = MAIN.read_text(encoding='utf-8')

# Visible redesign of the shared Android shell. Functional destinations stay unchanged.
replacements = [
    ('header.setPadding(dp(14), dp(8), dp(14), dp(8));', 'header.setPadding(dp(16), dp(10), dp(16), dp(10));'),
    ('header.setBackgroundColor(GREEN);', 'header.setBackgroundColor(Color.WHITE);\n        header.setElevation(dp(3));'),
    ('new LinearLayout.LayoutParams(dp(56), dp(56))', 'new LinearLayout.LayoutParams(dp(48), dp(48))'),
    ('TextView title = text("Clinica Digitale", 20, Color.WHITE, true);', 'TextView title = text("Clinica Digitale", 20, GREEN_DARK, true);'),
    ('menu.setTextColor(Color.WHITE);', 'menu.setTextColor(GREEN_DARK);'),
    ('menu.setBackground(roundRect(Color.argb(38, 255, 255, 255), Color.argb(80, 255, 255, 255), 10));', 'menu.setBackground(roundRect(Color.rgb(237, 247, 245), Color.rgb(190, 218, 212), 14));'),
    ('profileBar.setBackgroundColor(Color.WHITE);', 'profileBar.setBackgroundColor(Color.rgb(240, 247, 246));'),
    ('profileBar.addView(text("Profilo attivo", 12, MUTED, false));', 'profileBar.addView(text("Profilo", 12, MUTED, false));'),
    ('viewTitle = text("Panoramica", 23, TEXT, true);', 'viewTitle = text("Panoramica", 25, TEXT, true);'),
    ('content.setPadding(dp(16), dp(8), dp(16), dp(32));', 'content.setPadding(dp(16), dp(10), dp(16), dp(34));'),
    ('c.setBackground(roundRect(Color.WHITE, BORDER, 18));', 'c.setBackground(roundRect(Color.WHITE, BORDER, 20));'),
    ('c.setElevation(dp(2));', 'c.setElevation(dp(3));'),
    ('b.setBackground(roundRect(GREEN, GREEN_DARK, 13));', 'b.setBackground(roundRect(GREEN, GREEN_DARK, 15));'),
    ('b.setBackground(roundRect(Color.WHITE, Color.rgb(205, 219, 216), 13));', 'b.setBackground(roundRect(Color.WHITE, Color.rgb(205, 219, 216), 15));'),
]
for old, new in replacements:
    if old in main:
        main = main.replace(old, new)

panorama_sig = '    private void renderPanoramica() {'
require(main, panorama_sig, 'Panoramica method')

if 'private void addR58ModernHero()' not in main:
    method = r'''    private void addR58ModernHero() {
        LinearLayout hero = card();
        hero.setPadding(dp(18), dp(18), dp(18), dp(18));
        hero.setBackground(roundRect(Color.rgb(232, 246, 243), Color.rgb(181, 220, 212), 22));

        TextView eyebrow = text("CLINICA DIGITALE", 11, GREEN_DARK, true);
        if (Build.VERSION.SDK_INT >= 21) eyebrow.setLetterSpacing(0.08f);
        hero.addView(eyebrow);

        TextView h = text("Il tuo Dossier sanitario", 26, TEXT, true);
        h.setPadding(0, dp(5), 0, 0);
        hero.addView(h);

        TextView copy = text("Documenti, terapie, monitoraggi e imaging in un unico spazio, anche in mobilità.", 14, MUTED, false);
        copy.setPadding(0, dp(6), 0, 0);
        hero.addView(copy);

        int dicomCount = R27ExactWindows.dicomStudies(prefs).length();
        int imageCount = R27ExactWindows.mediaAttachments(prefs).length();
        LinearLayout chips = new LinearLayout(this);
        chips.setOrientation(LinearLayout.HORIZONTAL);
        chips.setPadding(0, dp(12), 0, 0);
        TextView syncChip = text("● Dossier sincronizzato", 12, GREEN_DARK, true);
        syncChip.setPadding(dp(10), dp(7), dp(10), dp(7));
        syncChip.setBackground(roundRect(Color.WHITE, Color.rgb(190, 218, 212), 16));
        chips.addView(syncChip, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        TextView mediaChip = text("Imaging " + dicomCount + " · Immagini " + imageCount, 12, GREEN_DARK, true);
        mediaChip.setPadding(dp(10), dp(7), dp(10), dp(7));
        mediaChip.setBackground(roundRect(Color.WHITE, Color.rgb(190, 218, 212), 16));
        LinearLayout.LayoutParams mp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        mp.setMargins(dp(8), 0, 0, 0);
        chips.addView(mediaChip, mp);
        hero.addView(chips);

        LinearLayout actions = new LinearLayout(this);
        actions.setOrientation(LinearLayout.HORIZONTAL);
        actions.setPadding(0, dp(14), 0, 0);
        Button docs = button("Documenti");
        docs.setOnClickListener(v -> navigateTo("Documenti"));
        actions.addView(docs, new LinearLayout.LayoutParams(0, dp(48), 1f));
        Button imaging = button("Imaging e media");
        imaging.setOnClickListener(v -> navigateTo("Imaging e media"));
        LinearLayout.LayoutParams ip = new LinearLayout.LayoutParams(0, dp(48), 1f);
        ip.setMargins(dp(8), 0, 0, 0);
        actions.addView(imaging, ip);
        hero.addView(actions);

        content.addView(hero, matchWrapBottom(14));
    }

'''
    main = main.replace(panorama_sig, method + panorama_sig, 1)

# Always place the hero at the beginning of Panoramica generated by the current R31+ chain.
if panorama_sig + '\n        addR58ModernHero();' not in main:
    main = main.replace(panorama_sig, panorama_sig + '\n        addR58ModernHero();', 1)

main = main.replace('.setTitle("Sezioni del Dossier")', '.setTitle("Vai a una sezione")')
main = main.replace('Button acquire = compactButton("Acquisisci");', 'Button acquire = compactButton("＋  Acquisisci");')
main = main.replace('Button importFile = compactButton("Importa file");', 'Button importFile = compactButton("⇧  Importa file");')
MAIN.write_text(main, encoding='utf-8')

# Media screen: visual refresh only. Storage preflight/copy/remove logic is frozen.
media = MEDIA.read_text(encoding='utf-8')
media = media.replace('header.setPadding(dp(16),dp(10),dp(16),dp(10));', 'header.setPadding(dp(16),dp(12),dp(16),dp(12));')
media = media.replace('header.setBackgroundColor(Color.WHITE);', 'header.setBackgroundColor(Color.WHITE);\n        header.setElevation(dp(3));')
media = media.replace('titles.addView(text("Imaging e media",22,TEXT,true));', 'titles.addView(text("Imaging e media",24,TEXT,true));')
media = media.replace('intro.addView(text(profileName,16,TEXT,true));', 'intro.setBackground(roundRect(Color.rgb(232,246,243),Color.rgb(181,220,212),22));\n        intro.addView(text("Archivio imaging",11,ACCENT_DARK,true));\n        intro.addView(text(profileName,20,TEXT,true),top(4));')
media = media.replace('private LinearLayout card(){LinearLayout c=new LinearLayout(this);c.setOrientation(LinearLayout.VERTICAL);c.setPadding(dp(16),dp(16),dp(16),dp(16));c.setBackground(roundRect(Color.WHITE,BORDER,18));c.setElevation(dp(2));return c;}', 'private LinearLayout card(){LinearLayout c=new LinearLayout(this);c.setOrientation(LinearLayout.VERTICAL);c.setPadding(dp(16),dp(16),dp(16),dp(16));c.setBackground(roundRect(Color.WHITE,BORDER,20));c.setElevation(dp(3));return c;}')
media = media.replace('roundRect(ACCENT,ACCENT_DARK,13)', 'roundRect(ACCENT,ACCENT_DARK,15)')
media = media.replace('roundRect(Color.WHITE,BORDER,13)', 'roundRect(Color.WHITE,BORDER,15)')
MEDIA.write_text(media, encoding='utf-8')

# Release identity.
gradle = GRADLE.read_text(encoding='utf-8')
gradle = re.sub(r'versionCode\s+57\b', 'versionCode 58', gradle, count=1)
gradle = gradle.replace("versionName '1.0.0-android-r57-sync-crash-media-fix-test'", "versionName '1.0.0-android-r58-modern-ui-media-test'")
require(gradle, 'versionCode 58', 'versionCode 58')
GRADLE.write_text(gradle, encoding='utf-8')

for p in Path('android-r3/app/src/test').rglob('*.java'):
    s = p.read_text(encoding='utf-8')
    ns = s.replace('versionCode 57', 'versionCode 58').replace('versionCode = 57', 'versionCode = 58')
    ns = ns.replace('1.0.0-android-r57-sync-crash-media-fix-test', '1.0.0-android-r58-modern-ui-media-test')
    if ns != s:
        p.write_text(ns, encoding='utf-8')

TEST.mkdir(parents=True, exist_ok=True)
(TEST / 'R58ModernUiMediaTest.java').write_text(r'''package it.dossiersanitario.clinicadigitale.beta;

import static org.junit.Assert.*;
import org.junit.Test;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;

public class R58ModernUiMediaTest {
    private String read(String p) throws Exception { return new String(Files.readAllBytes(Paths.get(p)), StandardCharsets.UTF_8); }

    @Test public void homeHasUnmistakableModernHeroAndImagingEntry() throws Exception {
        String main = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        assertTrue(main.contains("private void addR58ModernHero()"));
        assertTrue(main.contains("Il tuo Dossier sanitario"));
        assertTrue(main.contains("Dossier sincronizzato"));
        assertTrue(main.contains("Imaging e media"));
        assertTrue(main.contains("header.setBackgroundColor(Color.WHITE)"));
        assertTrue(main.contains("addR58ModernHero();"));
    }

    @Test public void imagingKeepsStoragePreflightAndGetsModernSurface() throws Exception {
        String media = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R56MediaActivity.java");
        assertTrue(media.contains("Archivio imaging"));
        assertTrue(media.contains("Spazio richiesto:"));
        assertTrue(media.contains("Spazio residuo previsto:"));
        assertTrue(media.contains("Rendi disponibile offline"));
        assertTrue(media.contains("header.setElevation(dp(3))"));
    }

    @Test public void r58IdentityIsUpgradeCompatible() throws Exception {
        String g = read("build.gradle");
        assertTrue(g.contains("versionCode 58"));
        assertTrue(g.contains("1.0.0-android-r58-modern-ui-media-test"));
    }
}
''', encoding='utf-8')

print('R58 v2 visible modern UI + imaging surface patch applied')
