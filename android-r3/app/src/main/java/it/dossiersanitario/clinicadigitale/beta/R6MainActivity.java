package it.dossiersanitario.clinicadigitale.beta;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.app.Dialog;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Color;
import android.graphics.Matrix;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.media.ExifInterface;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.provider.MediaStore;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.view.Window;
import android.widget.Button;
import android.widget.EditText;
import android.widget.GridLayout;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import java.io.File;
import java.text.SimpleDateFormat;
import java.util.ArrayDeque;
import java.util.Arrays;
import java.util.Comparator;
import java.util.Date;
import java.util.Deque;
import java.util.Locale;

public final class R6MainActivity extends Activity {
    private static final int CAMERA_PERMISSION = 5101;
    private static final int CAMERA_CAPTURE = 5102;
    private static final int EDIT_DOCUMENT = 5103;
    private static final String PREFS = "clinica_android_beta";

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
    private ScrollView mainScroll;
    private LinearLayout content;
    private TextView viewTitle;
    private TextView viewSubtitle;
    private TextView profileName;
    private TextView photoCount;
    private LinearLayout photoList;
    private EditText testField;
    private TextView savedValue;
    private String currentSection = "Panoramica";
    private final Deque<String> navigationHistory = new ArrayDeque<>();
    private File pendingCapture;
    private long lastPanoramicaBackMs = 0L;

    @Override protected void onCreate(Bundle state) {
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

    @Override protected void onSaveInstanceState(Bundle outState) {
        outState.putString("current_section", currentSection);
        super.onSaveInstanceState(outState);
    }

    @Override public void onBackPressed() {
        if (!navigationHistory.isEmpty()) {
            renderSection(navigationHistory.pop());
            return;
        }
        if (!"Panoramica".equals(currentSection)) {
            renderSection("Panoramica");
            return;
        }

        long now = System.currentTimeMillis();
        if (now - lastPanoramicaBackMs <= 2000L) {
            finishAndRemoveTask();
            return;
        }
        lastPanoramicaBackMs = now;
        Toast.makeText(this, "Premi di nuovo Indietro per uscire", Toast.LENGTH_SHORT).show();
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

        mainScroll = new ScrollView(this);
        mainScroll.setFillViewport(true);
        mainScroll.setBackgroundColor(PAGE);

        LinearLayout page = new LinearLayout(this);
        page.setOrientation(LinearLayout.VERTICAL);
        page.setBackgroundColor(PAGE);

        LinearLayout header = new LinearLayout(this);
        header.setOrientation(LinearLayout.HORIZONTAL);
        header.setGravity(Gravity.CENTER_VERTICAL);
        header.setPadding(dp(10), dp(5), dp(10), dp(5));
        header.setBackgroundColor(GREEN);

        ImageView icon = new ImageView(this);
        icon.setImageResource(R.drawable.dossier_sanitario);
        icon.setScaleType(ImageView.ScaleType.FIT_CENTER);
        header.addView(icon, new LinearLayout.LayoutParams(dp(92), dp(92)));

        TextView title = text("Dossier Sanitario", 24, Color.WHITE, true);
        title.setPadding(dp(8), 0, 0, 0);
        header.addView(title, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));

        Button menu = compactButton("☰  Sezioni");
        menu.setTextColor(Color.WHITE);
        menu.setBackground(roundRect(Color.argb(38, 255, 255, 255), Color.argb(80, 255, 255, 255), 10));
        menu.setOnClickListener(v -> showSectionsDialog());
        header.addView(menu, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, dp(46)));
        page.addView(header);

        LinearLayout profileBar = new LinearLayout(this);
        profileBar.setOrientation(LinearLayout.HORIZONTAL);
        profileBar.setGravity(Gravity.CENTER_VERTICAL);
        profileBar.setPadding(dp(16), dp(9), dp(16), dp(9));
        profileBar.setBackgroundColor(Color.WHITE);
        profileBar.addView(text("Profilo attivo", 12, MUTED, false));
        profileName = text(profileDisplayName(), 14, TEXT, true);
        profileName.setGravity(Gravity.END);
        profileBar.addView(profileName, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        page.addView(profileBar);

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
        importFile.setOnClickListener(v -> Toast.makeText(this, "Importazione file non ancora attiva nella R6", Toast.LENGTH_SHORT).show());
        quick.addView(importFile, ip);
        topbar.addView(quick);
        page.addView(topbar);

        content = new LinearLayout(this);
        content.setOrientation(LinearLayout.VERTICAL);
        content.setPadding(dp(16), dp(4), dp(16), dp(28));
        content.setBackgroundColor(PAGE);
        page.addView(content, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));

        mainScroll.addView(page, new ScrollView.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        root.addView(mainScroll, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f));
        return root;
    }

    private void showSectionsDialog() {
        int checked = Math.max(0, Arrays.asList(SECTIONS).indexOf(currentSection));
        new AlertDialog.Builder(this)
                .setTitle("Sezioni del Dossier")
                .setSingleChoiceItems(SECTIONS, checked, (dialog, which) -> {
                    dialog.dismiss();
                    navigateTo(SECTIONS[which]);
                })
                .setNegativeButton("Chiudi", null)
                .show();
    }

    private void navigateTo(String section) {
        if (section == null || section.equals(currentSection)) return;
        navigationHistory.push(currentSection);
        renderSection(section);
    }

    private void renderSection(String section) {
        currentSection = section;
        content.removeAllViews();
        photoCount = null;
        photoList = null;
        testField = null;
        savedValue = null;

        viewTitle.setText(section);
        viewSubtitle.setText(subtitleFor(section));

        switch (section) {
            case "Panoramica": renderPanoramica(); break;
            case "Dati profilo": renderDatiProfilo(); break;
            case "Documenti": renderDocumenti(); break;
            case "Monitoraggio": renderMonitoraggio(); break;
            case "Backup": renderBackup(); break;
            case "Aiuto": renderAiuto(); break;
            case "Logout": renderLogout(); break;
            default: renderStructuralSection(section); break;
        }
        if (mainScroll != null) mainScroll.post(() -> mainScroll.scrollTo(0, 0));
    }

    private String subtitleFor(String section) {
        switch (section) {
            case "Panoramica": return "Quadro sintetico del profilo sanitario attivo.";
            case "Dati profilo": return "Dati anagrafici e informazioni strutturate della persona.";
            case "Documenti": return "Archivio privato e scanner documentale integrato.";
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
        addMetric(grid, "Documenti recenti", String.valueOf(privatePhotoCount()));
        addMetric(grid, "Ultimo evento", "Nessuno");
        addMetric(grid, "Terapie attive", "0");
        addMetric(grid, "Ultimo backup", "Da configurare");
        content.addView(grid, matchWrapBottom(14));

        LinearLayout profileCard = card();
        profileCard.addView(sectionHeader("Dati del profilo"));
        profileCard.addView(labelValue("Profilo", profileDisplayName()));
        profileCard.addView(labelValue("Indirizzo", profileAddress()));
        Button edit = button("Apri dati profilo");
        edit.setOnClickListener(v -> navigateTo("Dati profilo"));
        profileCard.addView(edit, matchWrapTop(10));
        content.addView(profileCard, matchWrapBottom(14));

        LinearLayout recent = card();
        recent.addView(sectionHeader("Documenti recenti"));
        int count = privatePhotoCount();
        recent.addView(text(count == 0 ? "Nessun documento acquisito." : "Sono presenti " + count + " immagini private nel Dossier.", 14, MUTED, false));
        if (count > 0) {
            Button open = button("Apri documenti");
            open.setOnClickListener(v -> navigateTo("Documenti"));
            recent.addView(open, matchWrapTop(10));
        }
        content.addView(recent, matchWrapBottom(14));
    }

    private void addReleaseNotice() {
        LinearLayout notice = card();
        notice.setBackground(roundRect(Color.rgb(235, 247, 243), Color.rgb(183, 222, 210), 14));
        notice.addView(text("Android R6 TEST", 15, GREEN_DARK, true));
        notice.addView(text("Nuovo editor documentale privato: rotazione, ritaglio, correzione prospettica, correzione barilotto/cuscinetto e miglioramento leggibilità. Nessuna immagine viene pubblicata nella Galleria del telefono.", 13, MUTED, false));
        String inherited = prefs.getString("test_value", "").trim();
        if (!inherited.isEmpty() || privatePhotoCount() > 0) {
            notice.addView(text("Dati precedenti rilevati: " + (inherited.isEmpty() ? "testo assente" : "testo presente") + ", foto private: " + privatePhotoCount() + ".", 13, GREEN_DARK, true));
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
            Toast.makeText(this, "Dati profilo salvati", Toast.LENGTH_SHORT).show();
        });
        c.addView(save, matchWrapTop(12));
        content.addView(c, matchWrapBottom(14));
    }

    private void renderDocumenti() {
        LinearLayout c = card();
        c.addView(sectionHeader("Archivio documenti privato"));
        c.addView(text("Ogni foto resta nello spazio interno di Clinica Digitale. Dopo lo scatto si apre l'editor documentale prima del salvataggio definitivo.", 13, MUTED, false));

        Button camera = button("Fotografa un referto");
        camera.setOnClickListener(v -> requestCamera());
        c.addView(camera, matchWrapTop(10));

        photoCount = text("", 14, GREEN_DARK, true);
        photoCount.setPadding(0, dp(12), 0, dp(8));
        c.addView(photoCount);

        photoList = new LinearLayout(this);
        photoList.setOrientation(LinearLayout.VERTICAL);
        c.addView(photoList, matchWrap());
        content.addView(c, matchWrapBottom(14));

        LinearLayout legacy = card();
        legacy.addView(sectionHeader("Dato di prova conservato"));
        legacy.addView(text("Serve a verificare che gli aggiornamenti Android continuino a mantenere i dati locali.", 13, MUTED, false));
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

    private void refreshDocumentState() {
        if (savedValue != null) {
            String value = prefs.getString("test_value", "");
            savedValue.setText(value.isEmpty() ? "Nessun dato di prova salvato" : "Dato conservato: " + value);
            if (testField != null && !testField.hasFocus()) testField.setText(value);
        }

        File[] photos = privatePhotos();
        if (photos == null) photos = new File[0];
        Arrays.sort(photos, Comparator.comparingLong(File::lastModified).reversed());
        if (photoCount != null) photoCount.setText("Foto private presenti nel Dossier: " + photos.length);
        if (photoList == null) return;
        photoList.removeAllViews();

        if (photos.length == 0) {
            photoList.addView(text("Nessuna fotografia presente.", 13, MUTED, false));
            return;
        }

        SimpleDateFormat fmt = new SimpleDateFormat("dd/MM/yyyy HH:mm", Locale.ITALY);
        for (int i = 0; i < photos.length; i++) {
            File photo = photos[i];
            LinearLayout row = new LinearLayout(this);
            row.setOrientation(LinearLayout.HORIZONTAL);
            row.setGravity(Gravity.CENTER_VERTICAL);
            row.setPadding(dp(8), dp(8), dp(8), dp(8));
            row.setBackground(roundRect(Color.rgb(250, 252, 251), BORDER, 10));

            ImageView thumb = new ImageView(this);
            thumb.setScaleType(ImageView.ScaleType.CENTER_CROP);
            Bitmap bitmap = decodeScaledOriented(photo, 420, 420);
            if (bitmap != null) thumb.setImageBitmap(bitmap);
            row.addView(thumb, new LinearLayout.LayoutParams(dp(96), dp(96)));

            LinearLayout meta = new LinearLayout(this);
            meta.setOrientation(LinearLayout.VERTICAL);
            meta.setPadding(dp(12), 0, 0, 0);
            meta.addView(text("Documento fotografico " + (i + 1), 14, TEXT, true));
            meta.addView(text(fmt.format(new Date(photo.lastModified())), 12, MUTED, false));

            LinearLayout actions = new LinearLayout(this);
            actions.setOrientation(LinearLayout.HORIZONTAL);
            actions.setPadding(0, dp(7), 0, 0);
            Button open = compactButton("Apri");
            open.setOnClickListener(v -> showPhoto(photo));
            actions.addView(open, new LinearLayout.LayoutParams(0, dp(40), 1f));
            Button edit = compactButton("Modifica");
            LinearLayout.LayoutParams ep = new LinearLayout.LayoutParams(0, dp(40), 1f);
            ep.setMargins(dp(6), 0, 0, 0);
            edit.setOnClickListener(v -> launchEditor(photo, false));
            actions.addView(edit, ep);
            meta.addView(actions);

            row.addView(meta, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
            thumb.setOnClickListener(v -> showPhoto(photo));
            photoList.addView(row, matchWrapBottom(8));
        }
    }

    private void showPhoto(File photo) {
        Bitmap bitmap = decodeScaledOriented(photo, 2400, 2400);
        if (bitmap == null) {
            Toast.makeText(this, "Immagine non leggibile", Toast.LENGTH_SHORT).show();
            return;
        }
        Dialog dialog = new Dialog(this, android.R.style.Theme_Material_Light_NoActionBar_Fullscreen);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(Color.BLACK);

        Button close = new Button(this);
        close.setText("Chiudi");
        close.setAllCaps(false);
        close.setTextColor(Color.WHITE);
        close.setBackgroundColor(Color.rgb(35, 35, 35));
        close.setOnClickListener(v -> dialog.dismiss());
        root.addView(close, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(52)));

        ImageView full = new ImageView(this);
        full.setImageBitmap(bitmap);
        full.setScaleType(ImageView.ScaleType.FIT_CENTER);
        root.addView(full, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f));
        dialog.setContentView(root);
        dialog.show();
    }

    private void renderMonitoraggio() {
        LinearLayout intro = card();
        intro.addView(sectionHeader("Monitoraggio personale"));
        intro.addView(text("Le voci già testate restano disponibili nella struttura Android.", 13, MUTED, false));
        content.addView(intro, matchWrapBottom(14));

        String[] items = {"Percorso peso", "Glicemia", "Pressione", "Saturazione", "Misurazioni"};
        for (String item : items) {
            LinearLayout c = card();
            c.addView(text(item, 17, TEXT, true));
            c.addView(text(item.equals("Percorso peso") ? "Storico pesate, obiettivo, previsione e scostamento." : "Storico e andamento del parametro nel tempo.", 13, MUTED, false));
            Button b = button("Apri " + item.toLowerCase(Locale.ITALY));
            b.setOnClickListener(v -> Toast.makeText(this, item + ": struttura presente, modulo completo non ancora portato", Toast.LENGTH_SHORT).show());
            c.addView(b, matchWrapTop(9));
            content.addView(c, matchWrapBottom(12));
        }
    }

    private void renderBackup() {
        LinearLayout c = card();
        c.addView(sectionHeader("Continuità dei dati"));
        c.addView(text("R6 mantiene lo stesso pacchetto Android e la stessa firma beta delle release precedenti. Installala sopra la R5 senza disinstallare.", 14, TEXT, false));
        c.addView(text("La disinstallazione completa sul dispositivo Xiaomi continua a essere considerata non sicura per i dati finché Android non offre una scelta reale di conservazione.", 14, MUTED, false));
        content.addView(c, matchWrapBottom(14));
    }

    private void renderAiuto() {
        LinearLayout c = card();
        c.addView(sectionHeader("Aiuto R6"));
        c.addView(text("Dopo una foto usa Modifica documento: trascina i quattro punti sugli angoli del foglio, oppure usa Auto bordi. Sono disponibili rotazione, ritaglio, prospettiva, correzione barilotto/cuscinetto, miglioramento e ripristino.", 14, MUTED, false));
        content.addView(c, matchWrapBottom(14));
    }

    private void renderLogout() {
        LinearLayout c = card();
        c.addView(sectionHeader("Logout"));
        c.addView(text("L'associazione multiutente e al Dossier familiare/cloud non è ancora attiva in questa release.", 14, MUTED, false));
        Button back = button("Torna alla Panoramica");
        back.setOnClickListener(v -> navigateTo("Panoramica"));
        c.addView(back, matchWrapTop(10));
        content.addView(c, matchWrapBottom(14));
    }

    private void renderStructuralSection(String section) {
        LinearLayout c = card();
        c.addView(sectionHeader(section));
        c.addView(text(descriptionFor(section), 14, MUTED, false));
        TextView state = text("R6: struttura presente · funzione clinica completa non ancora attiva", 13, GREEN_DARK, true);
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
            case "Agenda": return "Visite, esami, scadenze e futura sincronizzazione con Google Calendar.";
            case "Preferenze": return "Impostazioni del profilo e comportamento dell'app.";
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

        if (requestCode == CAMERA_CAPTURE) {
            File temp = pendingCapture;
            pendingCapture = null;
            if (resultCode != RESULT_OK || temp == null || !temp.exists() || temp.length() == 0) {
                if (temp != null) temp.delete();
                cleanCameraTemp();
                Toast.makeText(this, "Acquisizione annullata", Toast.LENGTH_SHORT).show();
                return;
            }
            launchEditor(temp, true);
            return;
        }

        if (requestCode == EDIT_DOCUMENT) {
            cleanCameraTemp();
            if ("Documenti".equals(currentSection)) refreshDocumentState();
            if (resultCode == RESULT_OK) {
                Toast.makeText(this, "Documento salvato nel Dossier", Toast.LENGTH_SHORT).show();
            }
        }
    }

    private void launchEditor(File source, boolean newCapture) {
        Intent intent = new Intent(this, DocumentEditorActivity.class);
        intent.putExtra(DocumentEditorActivity.EXTRA_SOURCE_PATH, source.getAbsolutePath());
        intent.putExtra(DocumentEditorActivity.EXTRA_NEW_CAPTURE, newCapture);
        if (!newCapture) intent.putExtra(DocumentEditorActivity.EXTRA_REPLACE_PATH, source.getAbsolutePath());
        startActivityForResult(intent, EDIT_DOCUMENT);
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

    private static Bitmap decodeScaledOriented(File file, int maxW, int maxH) {
        BitmapFactory.Options bounds = new BitmapFactory.Options();
        bounds.inJustDecodeBounds = true;
        BitmapFactory.decodeFile(file.getAbsolutePath(), bounds);
        int sample = 1;
        while (bounds.outWidth / sample > maxW * 2 || bounds.outHeight / sample > maxH * 2) sample *= 2;
        BitmapFactory.Options opts = new BitmapFactory.Options();
        opts.inSampleSize = sample;
        Bitmap bitmap = BitmapFactory.decodeFile(file.getAbsolutePath(), opts);
        if (bitmap == null) return null;
        try {
            ExifInterface exif = new ExifInterface(file.getAbsolutePath());
            int o = exif.getAttributeInt(ExifInterface.TAG_ORIENTATION, ExifInterface.ORIENTATION_NORMAL);
            float deg = 0f;
            if (o == ExifInterface.ORIENTATION_ROTATE_90) deg = 90f;
            else if (o == ExifInterface.ORIENTATION_ROTATE_180) deg = 180f;
            else if (o == ExifInterface.ORIENTATION_ROTATE_270) deg = 270f;
            if (deg != 0f) {
                Matrix m = new Matrix();
                m.postRotate(deg);
                Bitmap rotated = Bitmap.createBitmap(bitmap, 0, 0, bitmap.getWidth(), bitmap.getHeight(), m, true);
                if (rotated != bitmap) bitmap.recycle();
                bitmap = rotated;
            }
        } catch (Exception ignored) { }
        return bitmap;
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
        row.addView(text(value, 13, TEXT, true), new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        return row;
    }

    private EditText field(String hint, String value) {
        EditText e = new EditText(this);
        e.setHint(hint);
        e.setText(value);
        e.setTextSize(15);
        e.setSingleLine(true);
        e.setPadding(dp(10), dp(8), dp(10), dp(8));
        e.setLayoutParams(matchWrapTop(6));
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

    private LinearLayout.LayoutParams matchWrap() {
        return new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
    }

    private LinearLayout.LayoutParams matchWrapBottom(int bottomDp) {
        LinearLayout.LayoutParams p = matchWrap();
        p.setMargins(0, 0, 0, dp(bottomDp));
        return p;
    }

    private LinearLayout.LayoutParams matchWrapTop(int topDp) {
        LinearLayout.LayoutParams p = matchWrap();
        p.setMargins(0, dp(topDp), 0, 0);
        return p;
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }
}
