package it.dossiersanitario.clinicadigitale.beta;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.provider.MediaStore;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.view.Window;
import android.view.WindowInsets;
import android.widget.Button;
import android.widget.EditText;
import android.widget.GridLayout;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.util.Arrays;
import java.util.Comparator;

public final class MainActivity extends Activity {
    private static final int CAMERA_PERMISSION = 5101;
    private static final int CAMERA_CAPTURE = 5102;
    private static final String PREFS = "clinica_android_beta"; // Must remain identical to R3.

    private static final int GREEN = Color.rgb(23, 138, 114);
    private static final int GREEN_DARK = Color.rgb(19, 110, 93);
    private static final int TEXT = Color.rgb(32, 48, 45);
    private static final int MUTED = Color.rgb(91, 105, 101);
    private static final int PAGE = Color.rgb(246, 249, 248);
    private static final int BORDER = Color.rgb(224, 232, 229);

    private static final String[] SECTIONS = {
            "Panoramica", "Dati profilo", "Esenzioni", "Documenti", "Cronologia",
            "Diagnosi", "Terapie", "Medici e specialisti", "Confronta", "Grafici",
            "Agenda", "Monitoraggio", "Preferenze", "Backup", "Aiuto", "Logout"
    };

    private SharedPreferences prefs;
    private LinearLayout content;
    private TextView viewTitle;
    private TextView viewSubtitle;
    private TextView profileName;
    private String currentSection = "Panoramica";

    private EditText testField;
    private TextView savedValue;
    private TextView photoCount;
    private ImageView preview;
    private File pendingCapture;

    @Override protected void onCreate(Bundle state) {
        super.onCreate(state);
        prefs = getSharedPreferences(PREFS, MODE_PRIVATE);
        cleanCameraTemp();

        Window w = getWindow();
        w.setStatusBarColor(GREEN_DARK);
        w.setNavigationBarColor(Color.WHITE);
        if (Build.VERSION.SDK_INT >= 23) {
            w.getDecorView().setSystemUiVisibility(0);
        }

        setContentView(buildUi());
        showSection("Panoramica");
    }

    private View buildUi() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(GREEN_DARK);
        root.setFitsSystemWindows(false);
        root.setOnApplyWindowInsetsListener((v, insets) -> {
            int top = insets.getSystemWindowInsetTop();
            int bottom = insets.getSystemWindowInsetBottom();
            v.setPadding(0, top, 0, bottom);
            return insets;
        });

        LinearLayout header = new LinearLayout(this);
        header.setOrientation(LinearLayout.HORIZONTAL);
        header.setGravity(Gravity.CENTER_VERTICAL);
        header.setPadding(dp(14), dp(10), dp(12), dp(10));
        header.setBackgroundColor(GREEN);

        ImageView icon = new ImageView(this);
        icon.setImageResource(R.drawable.dossier_sanitario);
        icon.setScaleType(ImageView.ScaleType.CENTER_INSIDE);
        header.addView(icon, new LinearLayout.LayoutParams(dp(50), dp(50)));

        LinearLayout titleBox = new LinearLayout(this);
        titleBox.setOrientation(LinearLayout.VERTICAL);
        titleBox.setPadding(dp(10), 0, 0, 0);
        TextView kicker = text("CLINICA DIGITALE", 12, Color.WHITE, true);
        kicker.setLetterSpacing(0.08f);
        titleBox.addView(kicker);
        titleBox.addView(text("Dossier Sanitario", 21, Color.WHITE, true));
        header.addView(titleBox, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));

        Button menu = compactButton("☰  Sezioni");
        menu.setTextColor(Color.WHITE);
        menu.setBackground(roundRect(Color.argb(38, 255, 255, 255), Color.argb(80, 255, 255, 255), 10));
        menu.setOnClickListener(v -> showSectionsDialog());
        header.addView(menu, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, dp(44)));
        root.addView(header);

        LinearLayout profileBar = new LinearLayout(this);
        profileBar.setOrientation(LinearLayout.HORIZONTAL);
        profileBar.setGravity(Gravity.CENTER_VERTICAL);
        profileBar.setPadding(dp(16), dp(9), dp(16), dp(9));
        profileBar.setBackgroundColor(Color.WHITE);
        TextView profileLabel = text("Profilo attivo", 12, MUTED, false);
        profileBar.addView(profileLabel);
        profileName = text(profileDisplayName(), 14, TEXT, true);
        profileName.setGravity(Gravity.END);
        profileBar.addView(profileName, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        root.addView(profileBar);

        LinearLayout topbar = new LinearLayout(this);
        topbar.setOrientation(LinearLayout.VERTICAL);
        topbar.setPadding(dp(16), dp(13), dp(16), dp(12));
        topbar.setBackgroundColor(PAGE);
        viewTitle = text("Panoramica", 24, TEXT, true);
        viewSubtitle = text("", 13, MUTED, false);
        viewSubtitle.setPadding(0, dp(3), 0, 0);
        topbar.addView(viewTitle);
        topbar.addView(viewSubtitle);

        LinearLayout quick = new LinearLayout(this);
        quick.setOrientation(LinearLayout.HORIZONTAL);
        quick.setPadding(0, dp(10), 0, 0);
        Button acquire = compactButton("Acquisisci");
        acquire.setOnClickListener(v -> requestCamera());
        quick.addView(acquire, new LinearLayout.LayoutParams(0, dp(44), 1f));
        Button importFile = compactButton("Importa file");
        LinearLayout.LayoutParams ip = new LinearLayout.LayoutParams(0, dp(44), 1f);
        ip.setMargins(dp(8), 0, 0, 0);
        importFile.setOnClickListener(v -> Toast.makeText(this, "Importazione file non ancora attiva nella R4 strutturale", Toast.LENGTH_SHORT).show());
        quick.addView(importFile, ip);
        topbar.addView(quick);
        root.addView(topbar);

        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        content = new LinearLayout(this);
        content.setOrientation(LinearLayout.VERTICAL);
        content.setPadding(dp(16), dp(4), dp(16), dp(28));
        content.setBackgroundColor(PAGE);
        scroll.addView(content, new ScrollView.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        root.addView(scroll, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f));
        return root;
    }

    private void showSectionsDialog() {
        int checked = Math.max(0, Arrays.asList(SECTIONS).indexOf(currentSection));
        new AlertDialog.Builder(this)
                .setTitle("Sezioni del Dossier")
                .setSingleChoiceItems(SECTIONS, checked, (dialog, which) -> {
                    dialog.dismiss();
                    showSection(SECTIONS[which]);
                })
                .setNegativeButton("Chiudi", null)
                .show();
    }

    private void showSection(String section) {
        currentSection = section;
        content.removeAllViews();
        testField = null;
        savedValue = null;
        photoCount = null;
        preview = null;

        viewTitle.setText(section);
        viewSubtitle.setText(subtitleFor(section));

        switch (section) {
            case "Panoramica": renderPanoramica(); break;
            case "Dati profilo": renderDatiProfilo(); break;
            case "Documenti": renderDocumenti(); break;
            case "Monitoraggio": renderMonitoraggio(); break;
            case "Backup": renderBackup(); break;
            case "Logout": renderLogout(); break;
            case "Aiuto": renderAiuto(); break;
            default: renderStructuralSection(section); break;
        }
    }

    private String subtitleFor(String section) {
        switch (section) {
            case "Panoramica": return "Quadro sintetico del profilo sanitario attivo.";
            case "Dati profilo": return "Dati anagrafici e informazioni strutturate della persona.";
            case "Documenti": return "Archivio privato di referti, immagini e documenti sanitari.";
            case "Agenda": return "Visite, esami, scadenze e promemoria.";
            case "Monitoraggio": return "Percorso peso e parametri personali nel tempo.";
            case "Backup": return "Protezione e continuità dei dati tra dispositivi e versioni.";
            default: return "Struttura Android collegata alla corrispondente sezione del Dossier Windows.";
        }
    }

    private void renderPanoramica() {
        addReleaseNotice();

        GridLayout grid = new GridLayout(this);
        grid.setColumnCount(2);
        grid.setUseDefaultMargins(false);
        addMetric(grid, "Documenti recenti", String.valueOf(privatePhotoCount()));
        addMetric(grid, "Ultimo evento", "Nessuno");
        addMetric(grid, "Terapie attive", "0");
        addMetric(grid, "Ultimo backup", "Da configurare");
        content.addView(grid, matchWrapBottom(14));

        LinearLayout profileCard = card();
        profileCard.addView(sectionHeader("Dati del profilo"));
        String name = profileDisplayName();
        profileCard.addView(labelValue("Profilo", name));
        profileCard.addView(labelValue("Indirizzo", profileAddress()));
        Button edit = button("Apri dati profilo");
        edit.setOnClickListener(v -> showSection("Dati profilo"));
        profileCard.addView(edit, matchWrapTop(10));
        content.addView(profileCard, matchWrapBottom(14));

        LinearLayout tessera = card();
        tessera.addView(sectionHeader("Tessera sanitaria"));
        tessera.addView(text("Nessuna tessera inserita nel profilo di test.", 14, MUTED, false));
        content.addView(tessera, matchWrapBottom(14));

        LinearLayout deadlines = card();
        deadlines.addView(sectionHeader("Prossime scadenze"));
        deadlines.addView(text("Nessuna scadenza registrata.", 14, MUTED, false));
        content.addView(deadlines, matchWrapBottom(14));

        LinearLayout recent = card();
        recent.addView(sectionHeader("Documenti recenti"));
        int count = privatePhotoCount();
        recent.addView(text(count == 0 ? "Nessun documento acquisito." : "Sono presenti " + count + " immagini private acquisite nel Dossier.", 14, MUTED, false));
        if (count > 0) {
            Button open = button("Apri documenti");
            open.setOnClickListener(v -> showSection("Documenti"));
            recent.addView(open, matchWrapTop(10));
        }
        content.addView(recent, matchWrapBottom(14));
    }

    private void addReleaseNotice() {
        LinearLayout notice = card();
        notice.setBackground(roundRect(Color.rgb(235, 247, 243), Color.rgb(183, 222, 210), 14));
        notice.addView(text("Android R4 TEST STRUTTURALE", 15, GREEN_DARK, true));
        notice.addView(text("La navigazione e la struttura del Dossier sono ora visibili. Le funzioni cliniche complete verranno portate progressivamente senza alterare la linea Windows stabile.", 13, MUTED, false));
        String inherited = prefs.getString("test_value", "").trim();
        if (!inherited.isEmpty() || privatePhotoCount() > 0) {
            notice.addView(text("Dati R3 rilevati: " + (inherited.isEmpty() ? "testo assente" : "testo presente") + ", foto private: " + privatePhotoCount() + ".", 13, GREEN_DARK, true));
        }
        content.addView(notice, matchWrapBottom(14));
    }

    private void addMetric(GridLayout grid, String title, String value) {
        LinearLayout box = card();
        box.setPadding(dp(13), dp(13), dp(13), dp(13));
        box.addView(text(title, 12, MUTED, false));
        TextView val = text(value, 17, TEXT, true);
        val.setPadding(0, dp(5), 0, 0);
        box.addView(val);
        GridLayout.LayoutParams p = new GridLayout.LayoutParams();
        p.width = 0;
        p.height = ViewGroup.LayoutParams.WRAP_CONTENT;
        p.columnSpec = GridLayout.spec(GridLayout.UNDEFINED, 1f);
        p.setMargins(0, 0, dp(8), dp(8));
        grid.addView(box, p);
    }

    private void renderDatiProfilo() {
        LinearLayout c = card();
        c.addView(sectionHeader("Dati anagrafici"));
        EditText nome = field("Nome", prefs.getString("profile_first_name", ""));
        EditText cognome = field("Cognome", prefs.getString("profile_last_name", ""));
        EditText data = field("Data di nascita", prefs.getString("profile_birth", ""));
        c.addView(nome); c.addView(cognome); c.addView(data);

        c.addView(sectionHeaderWithTop("Indirizzo", 14));
        EditText via = field("Via / indirizzo", prefs.getString("profile_address", ""));
        EditText cap = field("CAP", prefs.getString("profile_zip", ""));
        EditText city = field("Città", prefs.getString("profile_city", ""));
        EditText province = field("Provincia", prefs.getString("profile_province", ""));
        c.addView(via); c.addView(cap); c.addView(city); c.addView(province);

        Button save = button("Salva dati profilo");
        save.setOnClickListener(v -> {
            prefs.edit()
                    .putString("profile_first_name", clean(nome))
                    .putString("profile_last_name", clean(cognome))
                    .putString("profile_birth", clean(data))
                    .putString("profile_address", clean(via))
                    .putString("profile_zip", clean(cap))
                    .putString("profile_city", clean(city))
                    .putString("profile_province", clean(province))
                    .apply();
            profileName.setText(profileDisplayName());
            Toast.makeText(this, "Dati profilo salvati nello spazio privato", Toast.LENGTH_SHORT).show();
        });
        c.addView(save, matchWrapTop(12));
        content.addView(c, matchWrapBottom(14));
    }

    private void renderDocumenti() {
        LinearLayout c = card();
        c.addView(sectionHeader("Archivio documenti privato"));
        c.addView(text("Le fotografie acquisite restano nello spazio interno dell'app e non vengono pubblicate in Galleria, DCIM, Pictures o Download.", 13, MUTED, false));

        Button camera = button("Fotografa un referto");
        camera.setOnClickListener(v -> requestCamera());
        c.addView(camera, matchWrapTop(10));

        photoCount = text("", 14, GREEN_DARK, true);
        photoCount.setPadding(0, dp(12), 0, dp(8));
        c.addView(photoCount);
        preview = new ImageView(this);
        preview.setAdjustViewBounds(true);
        preview.setScaleType(ImageView.ScaleType.CENTER_INSIDE);
        c.addView(preview, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(230)));
        content.addView(c, matchWrapBottom(14));

        LinearLayout legacy = card();
        legacy.addView(sectionHeader("Controllo persistenza R3 → R4"));
        testField = field("Dato di prova", prefs.getString("test_value", ""));
        legacy.addView(testField);
        Button save = button("Salva dato di prova");
        save.setOnClickListener(v -> {
            prefs.edit().putString("test_value", clean(testField)).putLong("saved_at", System.currentTimeMillis()).apply();
            refreshDocumentState();
            Toast.makeText(this, "Dato salvato", Toast.LENGTH_SHORT).show();
        });
        legacy.addView(save, matchWrapTop(8));
        savedValue = text("", 13, GREEN_DARK, true);
        savedValue.setPadding(0, dp(10), 0, 0);
        legacy.addView(savedValue);
        content.addView(legacy, matchWrapBottom(14));
        refreshDocumentState();
    }

    private void renderMonitoraggio() {
        LinearLayout intro = card();
        intro.addView(sectionHeader("Monitoraggio personale"));
        intro.addView(text("Seleziona il percorso da aprire. In questa R4 la struttura è navigabile, mentre grafici e calcoli clinici completi non sono ancora attivi.", 13, MUTED, false));
        content.addView(intro, matchWrapBottom(14));

        String[] items = {"Percorso peso", "Glicemia", "Pressione", "Saturazione", "Misurazioni"};
        for (String item : items) {
            LinearLayout c = card();
            c.addView(text(item, 17, TEXT, true));
            c.addView(text(item.equals("Percorso peso") ? "Storico pesate, obiettivo, previsione e scostamento." : "Storico e andamento del parametro nel tempo.", 13, MUTED, false));
            Button b = button("Apri " + item.toLowerCase());
            b.setOnClickListener(v -> Toast.makeText(this, item + ": struttura presente, modulo funzionale non ancora portato", Toast.LENGTH_SHORT).show());
            c.addView(b, matchWrapTop(9));
            content.addView(c, matchWrapBottom(12));
        }
    }

    private void renderBackup() {
        LinearLayout c = card();
        c.addView(sectionHeader("Continuità dei dati"));
        c.addView(text("Installando la R4 sopra la R3, con lo stesso pacchetto e la stessa firma beta, Android conserva automaticamente i dati privati già presenti.", 14, TEXT, false));
        c.addView(text("Sul dispositivo Xiaomi testato la disinstallazione completa non offre invece l'opzione di mantenimento dati. Per questo la R4 non va disinstallata prima di aver definito e testato il meccanismo protetto di conservazione esterna o sincronizzazione.", 14, MUTED, false));
        content.addView(c, matchWrapBottom(14));
    }

    private void renderAiuto() {
        LinearLayout c = card();
        c.addView(sectionHeader("Aiuto"));
        c.addView(text("R4 Android: test della struttura mobile, persistenza tra aggiornamenti, icona ufficiale, area sicura superiore e archivio fotografico privato.", 14, MUTED, false));
        content.addView(c, matchWrapBottom(14));
    }

    private void renderLogout() {
        LinearLayout c = card();
        c.addView(sectionHeader("Logout"));
        c.addView(text("L'autenticazione multiutente e l'associazione al Dossier familiare/cloud non sono ancora attive in questa release strutturale.", 14, MUTED, false));
        Button back = button("Torna alla Panoramica");
        back.setOnClickListener(v -> showSection("Panoramica"));
        c.addView(back, matchWrapTop(10));
        content.addView(c, matchWrapBottom(14));
    }

    private void renderStructuralSection(String section) {
        LinearLayout c = card();
        c.addView(sectionHeader(section));
        c.addView(text(descriptionFor(section), 14, MUTED, false));
        TextView state = text("R4: struttura presente · funzione clinica completa non ancora attiva", 13, GREEN_DARK, true);
        state.setPadding(0, dp(12), 0, 0);
        c.addView(state);
        content.addView(c, matchWrapBottom(14));
    }

    private String descriptionFor(String section) {
        switch (section) {
            case "Esenzioni": return "Gestione delle esenzioni del profilo sanitario.";
            case "Cronologia": return "Sequenza cronologica di eventi, documenti e modifiche rilevanti.";
            case "Diagnosi": return "Quadro clinico principale e tabella completa delle diagnosi.";
            case "Terapie": return "Terapie attive, farmaci, dosaggi, orari e gestione delle scorte.";
            case "Medici e specialisti": return "Rubrica sanitaria del profilo con medici e specialisti di riferimento.";
            case "Confronta": return "Confronto preciso dei parametri tra documenti e date diverse.";
            case "Grafici": return "Andamento dei parametri sanitari nel tempo.";
            case "Agenda": return "Visite, esami, scadenze e sincronizzazione futura con Google Calendar.";
            case "Preferenze": return "Impostazioni del profilo, colore identificativo e comportamento dell'app.";
            default: return "Sezione del Dossier Sanitario.";
        }
    }

    private void requestCamera() {
        if (!getPackageManager().hasSystemFeature(PackageManager.FEATURE_CAMERA_ANY)) {
            Toast.makeText(this, "Fotocamera non disponibile su questo dispositivo", Toast.LENGTH_LONG).show();
            return;
        }
        if (checkSelfPermission(Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.CAMERA}, CAMERA_PERMISSION);
        } else {
            launchPrivateCamera();
        }
    }

    @Override public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == CAMERA_PERMISSION) {
            if (grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
                launchPrivateCamera();
            } else {
                Toast.makeText(this, "Senza autorizzazione alla fotocamera non posso acquisire il referto", Toast.LENGTH_LONG).show();
            }
        }
    }

    private void launchPrivateCamera() {
        cleanCameraTemp();
        File dir = new File(getCacheDir(), "clinica_camera");
        if (!dir.exists() && !dir.mkdirs()) {
            Toast.makeText(this, "Impossibile preparare la fotocamera", Toast.LENGTH_LONG).show();
            return;
        }
        pendingCapture = new File(dir, "capture_" + System.currentTimeMillis() + ".jpg");
        Uri uri = new Uri.Builder()
                .scheme("content")
                .authority(getPackageName() + ".fileprovider")
                .appendPath("camera")
                .appendPath(pendingCapture.getName())
                .build();

        Intent intent = new Intent(MediaStore.ACTION_IMAGE_CAPTURE);
        intent.putExtra(MediaStore.EXTRA_OUTPUT, uri);
        intent.addFlags(Intent.FLAG_GRANT_WRITE_URI_PERMISSION | Intent.FLAG_GRANT_READ_URI_PERMISSION);
        if (intent.resolveActivity(getPackageManager()) == null) {
            pendingCapture = null;
            Toast.makeText(this, "Applicazione fotocamera non disponibile", Toast.LENGTH_LONG).show();
            return;
        }
        startActivityForResult(intent, CAMERA_CAPTURE);
    }

    @Override protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode != CAMERA_CAPTURE) return;

        File temp = pendingCapture;
        pendingCapture = null;
        if (resultCode != RESULT_OK || temp == null || !temp.exists() || temp.length() == 0) {
            if (temp != null) temp.delete();
            cleanCameraTemp();
            Toast.makeText(this, "Acquisizione annullata", Toast.LENGTH_SHORT).show();
            return;
        }

        try {
            File target = new File(privateDocumentsDir(), "referto_foto_" + System.currentTimeMillis() + ".jpg");
            movePrivate(temp, target);
            cleanCameraTemp();
            if ("Documenti".equals(currentSection)) refreshDocumentState();
            Toast.makeText(this, "Foto salvata solo nel Dossier", Toast.LENGTH_LONG).show();
        } catch (IOException e) {
            temp.delete();
            cleanCameraTemp();
            Toast.makeText(this, "Salvataggio della foto non riuscito", Toast.LENGTH_LONG).show();
        }
    }

    private void refreshDocumentState() {
        if (savedValue != null) {
            String value = prefs.getString("test_value", "");
            savedValue.setText(value.isEmpty() ? "Nessun dato di prova salvato" : "Dato conservato: " + value);
            if (testField != null && !testField.hasFocus()) testField.setText(value);
        }
        if (photoCount != null) {
            File[] photos = privatePhotos();
            int count = photos == null ? 0 : photos.length;
            photoCount.setText("Foto private presenti nel Dossier: " + count);
            if (preview != null) {
                preview.setImageDrawable(null);
                if (photos != null && photos.length > 0) {
                    Arrays.sort(photos, Comparator.comparingLong(File::lastModified).reversed());
                    Bitmap bitmap = decodeScaled(photos[0], 1200, 800);
                    if (bitmap != null) preview.setImageBitmap(bitmap);
                }
            }
        }
    }

    private File[] privatePhotos() {
        return privateDocumentsDir().listFiles((d, n) -> n.startsWith("referto_foto_") && n.endsWith(".jpg"));
    }

    private int privatePhotoCount() {
        File[] files = privatePhotos();
        return files == null ? 0 : files.length;
    }

    private File privateDocumentsDir() {
        File dir = new File(getFilesDir(), "dossier_documents");
        if (!dir.exists()) dir.mkdirs();
        return dir;
    }

    private void cleanCameraTemp() {
        File dir = new File(getCacheDir(), "clinica_camera");
        File[] files = dir.listFiles();
        if (files != null) for (File f : files) f.delete();
        if (dir.exists()) dir.delete();
    }

    private String profileDisplayName() {
        String first = prefs.getString("profile_first_name", "").trim();
        String last = prefs.getString("profile_last_name", "").trim();
        String full = (first + " " + last).trim();
        return full.isEmpty() ? "Profilo test locale" : full;
    }

    private String profileAddress() {
        String via = prefs.getString("profile_address", "").trim();
        String cap = prefs.getString("profile_zip", "").trim();
        String city = prefs.getString("profile_city", "").trim();
        String prov = prefs.getString("profile_province", "").trim();
        String second = (cap + " " + city).trim();
        if (!prov.isEmpty()) second = second.isEmpty() ? prov : second + " (" + prov + ")";
        if (via.isEmpty() && second.isEmpty()) return "Non inserito";
        return via + (via.isEmpty() || second.isEmpty() ? "" : " · ") + second;
    }

    private static void movePrivate(File source, File target) throws IOException {
        if (source.renameTo(target)) return;
        try (FileInputStream in = new FileInputStream(source); FileOutputStream out = new FileOutputStream(target)) {
            byte[] buffer = new byte[64 * 1024];
            int n;
            while ((n = in.read(buffer)) > 0) out.write(buffer, 0, n);
            out.getFD().sync();
        }
        source.delete();
    }

    private static Bitmap decodeScaled(File file, int maxW, int maxH) {
        BitmapFactory.Options bounds = new BitmapFactory.Options();
        bounds.inJustDecodeBounds = true;
        BitmapFactory.decodeFile(file.getAbsolutePath(), bounds);
        int sample = 1;
        while (bounds.outWidth / sample > maxW * 2 || bounds.outHeight / sample > maxH * 2) sample *= 2;
        BitmapFactory.Options opts = new BitmapFactory.Options();
        opts.inSampleSize = sample;
        return BitmapFactory.decodeFile(file.getAbsolutePath(), opts);
    }

    private LinearLayout card() {
        LinearLayout c = new LinearLayout(this);
        c.setOrientation(LinearLayout.VERTICAL);
        c.setPadding(dp(15), dp(15), dp(15), dp(15));
        c.setBackground(roundRect(Color.WHITE, BORDER, 14));
        c.setElevation(dp(1));
        return c;
    }

    private TextView sectionHeader(String s) {
        TextView v = text(s, 18, TEXT, true);
        v.setPadding(0, 0, 0, dp(9));
        return v;
    }

    private TextView sectionHeaderWithTop(String s, int topDp) {
        TextView v = text(s, 17, TEXT, true);
        v.setPadding(0, dp(topDp), 0, dp(8));
        return v;
    }

    private LinearLayout labelValue(String label, String value) {
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setPadding(0, dp(5), 0, dp(5));
        row.addView(text(label, 13, MUTED, false), new LinearLayout.LayoutParams(dp(92), ViewGroup.LayoutParams.WRAP_CONTENT));
        TextView val = text(value, 13, TEXT, true);
        row.addView(val, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        return row;
    }

    private EditText field(String hint, String value) {
        EditText e = new EditText(this);
        e.setHint(hint);
        e.setText(value);
        e.setTextSize(15);
        e.setSingleLine(true);
        e.setPadding(dp(10), dp(8), dp(10), dp(8));
        LinearLayout.LayoutParams p = matchWrapTop(6);
        e.setLayoutParams(p);
        return e;
    }

    private String clean(EditText e) {
        return e.getText().toString().trim();
    }

    private Button button(String label) {
        Button b = new Button(this);
        b.setText(label);
        b.setAllCaps(false);
        b.setTextSize(14);
        b.setTextColor(Color.WHITE);
        b.setBackground(roundRect(GREEN, GREEN_DARK, 10));
        b.setPadding(dp(10), 0, dp(10), 0);
        return b;
    }

    private Button compactButton(String label) {
        Button b = new Button(this);
        b.setText(label);
        b.setAllCaps(false);
        b.setTextSize(13);
        b.setTextColor(GREEN_DARK);
        b.setBackground(roundRect(Color.WHITE, Color.rgb(195, 214, 208), 10));
        b.setPadding(dp(10), 0, dp(10), 0);
        return b;
    }

    private TextView text(String s, int sp, int color, boolean bold) {
        TextView v = new TextView(this);
        v.setText(s);
        v.setTextSize(sp);
        v.setTextColor(color);
        if (bold) v.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        v.setLineSpacing(0, 1.12f);
        return v;
    }

    private GradientDrawable roundRect(int fill, int stroke, int radiusDp) {
        GradientDrawable g = new GradientDrawable();
        g.setColor(fill);
        g.setCornerRadius(dp(radiusDp));
        g.setStroke(dp(1), stroke);
        return g;
    }

    private LinearLayout.LayoutParams matchWrapBottom(int bottomDp) {
        LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        p.setMargins(0, 0, 0, dp(bottomDp));
        return p;
    }

    private LinearLayout.LayoutParams matchWrapTop(int topDp) {
        LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        p.setMargins(0, dp(topDp), 0, 0);
        return p;
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }
}
