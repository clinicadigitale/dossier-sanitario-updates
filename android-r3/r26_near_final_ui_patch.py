from pathlib import Path

BASE = Path('android-r3/app/src/main/java/it/dossiersanitario/clinicadigitale/beta')
MAIN = BASE / 'R6MainActivity.java'
MANIFEST = Path('android-r3/app/src/main/AndroidManifest.xml')
GRADLE = Path('android-r3/app/build.gradle')


def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit(f'R26 UI patch failed: missing {label}')
    return text.replace(old, new, 1)


s = MAIN.read_text(encoding='utf-8')

# Dynamic imported theme instead of hard-coded-only colors.
s = replace_once(s, '    private static final int GREEN = Color.rgb(23, 138, 114);\n    private static final int GREEN_DARK = Color.rgb(19, 110, 93);',
'''    private int GREEN = Color.rgb(23, 138, 114);
    private int GREEN_DARK = Color.rgb(19, 110, 93);''', 'dynamic theme colors')

# Health-card request codes.
request_marker = '    private static final int EDIT_DOCUMENT = 5103;\n'
s = replace_once(s, request_marker, request_marker +
'''    private static final int HEALTH_CARD_FRONT = 5401;
    private static final int HEALTH_CARD_BACK = 5402;
''', 'health card request codes')

# Session timeout state; credentials remain untouched and remembered exactly as R25.
session_marker = '    private boolean sessionAuthenticated = false;\n'
session_fields = r'''    private boolean sessionAuthenticated = false;
    private final android.os.Handler r26SessionHandler = new android.os.Handler(android.os.Looper.getMainLooper());
    private long r26LastInteractionAt = System.currentTimeMillis();
    private int r26SessionTimeoutMinutes = 15;
    private final Runnable r26TimeoutRunnable = new Runnable() {
        @Override public void run() {
            if (!sessionAuthenticated) return;
            long timeoutMs = Math.max(1L, r26SessionTimeoutMinutes) * 60_000L;
            long elapsed = System.currentTimeMillis() - r26LastInteractionAt;
            if (elapsed >= timeoutMs) {
                sessionAuthenticated = false;
                showStartupGate(null);
                return;
            }
            r26SessionHandler.postDelayed(this, Math.max(1000L, timeoutMs - elapsed));
        }
    };
'''
s = replace_once(s, session_marker, session_fields, 'session timeout state')

# Load Windows color/timeout immediately after local prefs are available.
startup_marker = '        prefs = getSharedPreferences(PREFS, MODE_PRIVATE);\n        cleanCameraTemp();\n'
s = replace_once(s, startup_marker, startup_marker + '        loadR26ImportedUiSettings();\n', 'R26 imported UI settings startup')

# Switch all previously structural sections to real implementations.
switch_marker = '''            case "Agenda": renderAgenda(); break;\n            case "Preferenze": renderPreferenze(); break;\n            case "Monitoraggio": renderMonitoraggio(); break;'''
switch_new = '''            case "Diagnosi": renderDiagnosi(); break;\n            case "Terapie": renderTerapie(); break;\n            case "Confronta": renderConfronta(); break;\n            case "Grafici": renderGrafici(); break;\n            case "Agenda": renderAgenda(); break;\n            case "Preferenze": renderPreferenze(); break;\n            case "Monitoraggio": renderMonitoraggio(); break;'''
s = replace_once(s, switch_marker, switch_new, 'complete section switch')

# Dashboard must use imported Dossier data, never hard-coded zero values.
s = s.replace('        addMetric(grid, "Documenti recenti", String.valueOf(privatePhotoCount()));',
              '        addMetric(grid, "Documenti recenti", String.valueOf(Math.max(privatePhotoCount(), R12CloudManager.cloudDocumentCount(prefs))));')
s = s.replace('        addMetric(grid, "Terapie attive", "0");',
              '        addMetric(grid, "Terapie attive", String.valueOf(R26SnapshotBridge.countActive(R26SnapshotBridge.therapies(prefs))));')
s = s.replace('        addMetric(grid, "Ultimo backup", "Da configurare");',
              '        addMetric(grid, "Ultimo backup", R12CloudManager.lastSyncLabel(prefs));')
s = s.replace('        addMetric(grid, "Ultimo evento", latestEventSummary());',
              '        String r26Latest = R26SnapshotBridge.latestLabel(R26SnapshotBridge.clinicalEvents(prefs));\n        addMetric(grid, "Ultimo evento", "Nessuno".equals(r26Latest) ? latestEventSummary() : r26Latest);')

# Wrap Profile, Preferences and Monitoring instead of discarding their already working parts.
s = replace_once(s, '    private void renderDatiProfilo() {', '    private void renderDatiProfiloBase() {', 'rename profile base')
s = replace_once(s, '    private void renderPreferenze() {', '    private void renderPreferenzeBase() {', 'rename preferences base')
s = replace_once(s, '    private void renderMonitoraggio() {', '    private void renderMonitoraggioBase() {', 'rename monitoring base')

# Session starts/restarts only after authentication; no login loss on normal UI rebuild.
main_ui_marker = '''    private void showMainUi(Bundle state) {
        if (!sessionAuthenticated) {
            showStartupGate(state);
            return;
        }
        setContentView(buildUi());'''
main_ui_new = '''    private void showMainUi(Bundle state) {
        if (!sessionAuthenticated) {
            showStartupGate(state);
            return;
        }
        r26LastInteractionAt = System.currentTimeMillis();
        scheduleR26TimeoutCheck();
        setContentView(buildUi());'''
s = replace_once(s, main_ui_marker, main_ui_new, 'session timeout main UI hook')

# onDestroy already exists from R10; keep executor shutdown and clear timeout callbacks too.
destroy_marker = '''    @Override protected void onDestroy() {
        dataExecutor.shutdown();
        super.onDestroy();
    }'''
destroy_new = '''    @Override protected void onDestroy() {
        r26SessionHandler.removeCallbacks(r26TimeoutRunnable);
        dataExecutor.shutdown();
        super.onDestroy();
    }'''
s = replace_once(s, destroy_marker, destroy_new, 'timeout cleanup')

# Health card import result is handled before the older document/editor routes.
activity_result_marker = '        super.onActivityResult(requestCode, resultCode, data);\n'
activity_result_new = activity_result_marker + r'''        if (requestCode == HEALTH_CARD_FRONT || requestCode == HEALTH_CARD_BACK) {
            if (resultCode == RESULT_OK && data != null && data.getData() != null) {
                try {
                    saveHealthCardUri(data.getData(), requestCode == HEALTH_CARD_FRONT);
                    Toast.makeText(this, "Tessera Sanitaria salvata", Toast.LENGTH_SHORT).show();
                    if ("Dati profilo".equals(currentSection)) renderSection("Dati profilo");
                } catch (Exception e) {
                    Toast.makeText(this, "Salvataggio Tessera Sanitaria non riuscito", Toast.LENGTH_LONG).show();
                }
            }
            return;
        }
'''
s = replace_once(s, activity_result_marker, activity_result_new, 'health card activity result')

# Insert R26 methods just before Backup, a stable insertion point after Preferences.
insert_marker = '    private void renderBackup() {'
if insert_marker not in s:
    raise SystemExit('R26 UI patch failed: renderBackup insertion point missing')

methods = r'''    private void loadR26ImportedUiSettings() {
        int imported = R26SnapshotBridge.themeColor(prefs, Color.rgb(23, 138, 114));
        String override = prefs.getString("r26_theme_override", "");
        if (override != null && override.matches("#[0-9A-Fa-f]{6}")) {
            try { imported = Color.parseColor(override); } catch (Exception ignored) {}
        }
        GREEN = imported;
        GREEN_DARK = darkenR26(imported, 0.80f);
        r26SessionTimeoutMinutes = prefs.getInt("r26_timeout_override", R26SnapshotBridge.timeoutMinutes(prefs, 15));
    }

    private int darkenR26(int color, float factor) {
        return Color.rgb(Math.max(0, Math.min(255, Math.round(Color.red(color) * factor))),
                Math.max(0, Math.min(255, Math.round(Color.green(color) * factor))),
                Math.max(0, Math.min(255, Math.round(Color.blue(color) * factor))));
    }

    private void scheduleR26TimeoutCheck() {
        r26SessionHandler.removeCallbacks(r26TimeoutRunnable);
        if (sessionAuthenticated) r26SessionHandler.postDelayed(r26TimeoutRunnable, Math.max(1000L, r26SessionTimeoutMinutes * 60_000L));
    }

    @Override public void onUserInteraction() {
        super.onUserInteraction();
        if (sessionAuthenticated) {
            r26LastInteractionAt = System.currentTimeMillis();
            scheduleR26TimeoutCheck();
        }
    }

    @Override protected void onResume() {
        super.onResume();
        if (sessionAuthenticated) {
            long timeoutMs = Math.max(1L, r26SessionTimeoutMinutes) * 60_000L;
            if (System.currentTimeMillis() - r26LastInteractionAt >= timeoutMs) {
                sessionAuthenticated = false;
                showStartupGate(null);
            } else scheduleR26TimeoutCheck();
        }
    }

    @Override protected void onPause() {
        r26SessionHandler.removeCallbacks(r26TimeoutRunnable);
        super.onPause();
    }

    private void renderDatiProfilo() {
        renderDatiProfiloBase();
        renderHealthCard();
    }

    private void renderHealthCard() {
        LinearLayout c = card();
        c.addView(sectionHeader("Tessera Sanitaria"));
        c.addView(text("Fronte e retro fanno parte del profilo sanitario e restano nello spazio privato del Dossier.", 13, MUTED, false));

        File front = healthCardLocalFile(true);
        File back = healthCardLocalFile(false);
        JSONArray imported = R26SnapshotBridge.healthCardEntries(prefs);
        String importedFront = "", importedBack = "";
        for (int i = 0; i < imported.length(); i++) {
            String path = imported.optString(i, "");
            String lower = path.toLowerCase(Locale.ROOT);
            if (lower.contains("retro") || lower.contains("back")) importedBack = path;
            else if (importedFront.isEmpty()) importedFront = path;
            else if (importedBack.isEmpty()) importedBack = path;
        }

        if (front.isFile()) c.addView(healthCardPreview(front, "Fronte"));
        else if (!importedFront.isEmpty()) {
            final String path = importedFront;
            Button openFront = button("Apri fronte importato");
            openFront.setOnClickListener(v -> R12CloudManager.openSnapshotPath(this, prefs, path, guessImageMime(path), "fronte Tessera Sanitaria"));
            c.addView(openFront, matchWrapTop(8));
        } else c.addView(text("Fronte non presente.", 13, MUTED, false));

        Button loadFront = button(front.isFile() || !importedFront.isEmpty() ? "Carica o sostituisci fronte" : "Carica fronte");
        loadFront.setOnClickListener(v -> chooseHealthCardFile(true));
        c.addView(loadFront, matchWrapTop(8));

        if (back.isFile()) c.addView(healthCardPreview(back, "Retro"));
        else if (!importedBack.isEmpty()) {
            final String path = importedBack;
            Button openBack = button("Mostra retro");
            openBack.setOnClickListener(v -> R12CloudManager.openSnapshotPath(this, prefs, path, guessImageMime(path), "retro Tessera Sanitaria"));
            c.addView(openBack, matchWrapTop(8));
        } else c.addView(text("Retro non presente.", 13, MUTED, false));

        Button loadBack = button(back.isFile() || !importedBack.isEmpty() ? "Carica o sostituisci retro" : "Carica retro");
        loadBack.setOnClickListener(v -> chooseHealthCardFile(false));
        c.addView(loadBack, matchWrapTop(8));
        content.addView(c, matchWrapBottom(14));
    }

    private View healthCardPreview(File file, String label) {
        LinearLayout box = new LinearLayout(this);
        box.setOrientation(LinearLayout.VERTICAL);
        box.setPadding(0, dp(10), 0, 0);
        box.addView(text(label, 13, GREEN_DARK, true));
        Bitmap bitmap = BitmapFactory.decodeFile(file.getAbsolutePath());
        if (bitmap != null) {
            ImageView image = new ImageView(this);
            image.setImageBitmap(bitmap);
            image.setAdjustViewBounds(true);
            image.setScaleType(ImageView.ScaleType.FIT_CENTER);
            box.addView(image, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(180)));
        }
        return box;
    }

    private File healthCardLocalFile(boolean front) {
        File dir = new File(getFilesDir(), "dossier_profile");
        if (!dir.exists()) dir.mkdirs();
        File[] files = dir.listFiles((d, n) -> n.startsWith(front ? "health_card_front." : "health_card_back."));
        return files != null && files.length > 0 ? files[0] : new File(dir, front ? "health_card_front.jpg" : "health_card_back.jpg");
    }

    private void chooseHealthCardFile(boolean front) {
        Intent i = new Intent(Intent.ACTION_OPEN_DOCUMENT);
        i.addCategory(Intent.CATEGORY_OPENABLE);
        i.setType("image/*");
        startActivityForResult(i, front ? HEALTH_CARD_FRONT : HEALTH_CARD_BACK);
    }

    private void saveHealthCardUri(Uri uri, boolean front) throws Exception {
        String mime = getContentResolver().getType(uri);
        String ext = mime != null && mime.contains("png") ? ".png" : mime != null && mime.contains("webp") ? ".webp" : ".jpg";
        File dir = new File(getFilesDir(), "dossier_profile");
        if (!dir.exists() && !dir.mkdirs()) throw new Exception("Cartella profilo non disponibile");
        File[] previous = dir.listFiles((d, n) -> n.startsWith(front ? "health_card_front." : "health_card_back."));
        if (previous != null) for (File p : previous) p.delete();
        File target = new File(dir, (front ? "health_card_front" : "health_card_back") + ext);
        try (java.io.InputStream in = getContentResolver().openInputStream(uri); java.io.FileOutputStream out = new java.io.FileOutputStream(target)) {
            if (in == null) throw new Exception("Immagine non leggibile");
            byte[] buffer = new byte[65536]; int n;
            while ((n = in.read(buffer)) >= 0) out.write(buffer, 0, n);
            out.getFD().sync();
        }
        if (!target.isFile() || target.length() == 0) throw new Exception("Immagine vuota");
    }

    private String guessImageMime(String path) {
        String lower = String.valueOf(path).toLowerCase(Locale.ROOT);
        if (lower.endsWith(".png")) return "image/png";
        if (lower.endsWith(".webp")) return "image/webp";
        return "image/jpeg";
    }

    private void renderDiagnosi() {
        renderImportedRecordsSection("Diagnosi", "Quadro clinico importato dal Dossier Windows.", R26SnapshotBridge.diagnoses(prefs), "Nessuna diagnosi registrata nel profilo sincronizzato.");
    }

    private void renderTerapie() {
        JSONArray records = R26SnapshotBridge.therapies(prefs);
        LinearLayout summary = card();
        summary.addView(sectionHeader("Terapie"));
        summary.addView(labelValue("Terapie attive", String.valueOf(R26SnapshotBridge.countActive(records))));
        summary.addView(text("Farmaci, dosaggi e stato vengono letti direttamente dalla copia sincronizzata del Dossier.", 13, MUTED, false));
        content.addView(summary, matchWrapBottom(14));
        renderImportedRecordCards(records, "Terapia");
    }

    private void renderConfronta() {
        LinearLayout intro = card();
        intro.addView(sectionHeader("Confronta"));
        intro.addView(text("Confronto tra le ultime due rilevazioni disponibili per ciascun parametro sincronizzato.", 13, MUTED, false));
        content.addView(intro, matchWrapBottom(14));
        renderComparison("Peso", R26SnapshotBridge.weightRecords(prefs), new String[]{"peso", "weight", "value", "valore"});
        renderComparison("Glicemia", R26SnapshotBridge.glucoseRecords(prefs), new String[]{"glicemia", "glucose", "value", "valore"});
        renderComparison("Pressione", R26SnapshotBridge.pressureRecords(prefs), new String[]{"sistolica", "systolic", "value", "valore"});
        renderComparison("Saturazione", R26SnapshotBridge.saturationRecords(prefs), new String[]{"saturazione", "spo2", "value", "valore"});
    }

    private void renderComparison(String titleText, JSONArray records, String[] keys) {
        if (records == null || records.length() < 2) return;
        JSONObject latest = records.optJSONObject(records.length() - 1);
        JSONObject previous = records.optJSONObject(records.length() - 2);
        double a = R26SnapshotBridge.numericValue(latest, keys);
        double b = R26SnapshotBridge.numericValue(previous, keys);
        if (Double.isNaN(a) || Double.isNaN(b)) return;
        LinearLayout c = card();
        c.addView(sectionHeader(titleText));
        c.addView(labelValue("Precedente", formatR26Number(b)));
        c.addView(labelValue("Ultima", formatR26Number(a)));
        c.addView(labelValue("Differenza", (a - b >= 0 ? "+" : "") + formatR26Number(a - b)));
        content.addView(c, matchWrapBottom(12));
    }

    private String formatR26Number(double v) {
        if (Math.abs(v - Math.rint(v)) < 0.05) return String.valueOf((long)Math.rint(v));
        return String.format(Locale.ITALY, "%.1f", v);
    }

    private void renderGrafici() {
        LinearLayout intro = card();
        intro.addView(sectionHeader("Grafici"));
        intro.addView(text("I grafici usano i dati reali importati dal Dossier Windows e si aggiornano con le sincronizzazioni successive.", 13, MUTED, false));
        content.addView(intro, matchWrapBottom(14));
        addR26Chart("Percorso peso", R26SnapshotBridge.weightRecords(prefs), new String[]{"peso", "weight", "value", "valore"});
        addR26Chart("Glicemia", R26SnapshotBridge.glucoseRecords(prefs), new String[]{"glicemia", "glucose", "value", "valore"});
        addR26Chart("Pressione sistolica", R26SnapshotBridge.pressureRecords(prefs), new String[]{"sistolica", "systolic", "sys", "value", "valore"});
        addR26Chart("Saturazione", R26SnapshotBridge.saturationRecords(prefs), new String[]{"saturazione", "spo2", "oxygen", "value", "valore"});
    }

    private void addR26Chart(String titleText, JSONArray records, String[] keys) {
        if (records == null || records.length() == 0) return;
        LinearLayout c = card();
        c.addView(sectionHeader(titleText));
        R26ChartView chart = new R26ChartView(this, records, GREEN, keys);
        c.addView(chart, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(230)));
        content.addView(c, matchWrapBottom(14));
    }

    private void renderMonitoraggio() {
        JSONArray weight = R26SnapshotBridge.weightRecords(prefs);
        JSONArray glucose = R26SnapshotBridge.glucoseRecords(prefs);
        JSONArray pressure = R26SnapshotBridge.pressureRecords(prefs);
        JSONArray saturation = R26SnapshotBridge.saturationRecords(prefs);
        JSONArray generic = R26SnapshotBridge.genericMonitoringRecords(prefs);
        if (weight.length() + glucose.length() + pressure.length() + saturation.length() + generic.length() == 0) {
            renderMonitoraggioBase();
            return;
        }
        LinearLayout intro = card();
        intro.addView(sectionHeader("Monitoraggio"));
        intro.addView(text("Storici sincronizzati dal Dossier Windows.", 13, MUTED, false));
        content.addView(intro, matchWrapBottom(14));
        renderMonitoringDataset("Percorso peso", weight);
        renderMonitoringDataset("Glicemia", glucose);
        renderMonitoringDataset("Pressione", pressure);
        renderMonitoringDataset("Saturazione", saturation);
        if (generic.length() > 0) renderMonitoringDataset("Altri parametri", generic);
    }

    private void renderMonitoringDataset(String titleText, JSONArray records) {
        if (records == null || records.length() == 0) return;
        LinearLayout c = card();
        c.addView(sectionHeader(titleText));
        c.addView(labelValue("Rilevazioni", String.valueOf(records.length())));
        int start = Math.max(0, records.length() - 8);
        for (int i = records.length() - 1; i >= start; i--) {
            JSONObject row = records.optJSONObject(i);
            if (row == null) continue;
            String title = R26SnapshotBridge.recordTitle(row, "Rilevazione");
            String sub = R26SnapshotBridge.recordSubtitle(row);
            c.addView(text(title + (sub.isEmpty() ? "" : " · " + sub), 13, TEXT, false));
        }
        content.addView(c, matchWrapBottom(12));
    }

    private void renderPreferenze() {
        renderPreferenzeBase();
        renderWindowsPreferences();
    }

    private void renderWindowsPreferences() {
        LinearLayout c = card();
        c.addView(sectionHeader("Aspetto e impostazioni del Dossier"));
        int importedColor = R26SnapshotBridge.themeColor(prefs, GREEN);
        TextView swatch = text("Colore del Dossier importato da Windows", 14, Color.WHITE, true);
        swatch.setPadding(dp(12), dp(12), dp(12), dp(12));
        swatch.setBackgroundColor(importedColor);
        c.addView(swatch, matchWrapTop(8));

        String selected = R26SnapshotBridge.selectedUsersSummary(prefs);
        c.addView(labelValue("Utenti selezionati", selected.isEmpty() ? "Impostazione Windows non disponibile nello snapshot" : selected));
        c.addView(labelValue("Timeout sessione", r26SessionTimeoutMinutes + " minuti"));

        JSONArray userColors = R26SnapshotBridge.userColorRows(prefs);
        if (userColors.length() > 0) {
            c.addView(sectionHeaderWithTop("Colori utenti", 14));
            for (int i = 0; i < userColors.length(); i++) {
                JSONObject row = userColors.optJSONObject(i);
                if (row == null) continue;
                TextView user = text(row.optString("name", "Utente"), 13, Color.WHITE, true);
                user.setPadding(dp(10), dp(8), dp(10), dp(8));
                user.setBackgroundColor(row.optInt("color", GREEN));
                c.addView(user, matchWrapTop(6));
            }
        }

        Button color = button("Imposta colore interfaccia");
        color.setOnClickListener(v -> showR26ColorPicker());
        c.addView(color, matchWrapTop(10));
        Button timeout = button("Imposta timeout di sicurezza");
        timeout.setOnClickListener(v -> showR26TimeoutPicker());
        c.addView(timeout, matchWrapTop(8));
        content.addView(c, matchWrapBottom(14));

        JSONObject settings = R26SnapshotBridge.windowsSettings(prefs);
        if (settings.length() > 0) {
            LinearLayout raw = card();
            raw.addView(sectionHeader("Preferenze importate dalla versione Windows"));
            java.util.Iterator<String> keys = settings.keys();
            int shown = 0;
            while (keys.hasNext() && shown < 18) {
                String key = keys.next();
                Object value = settings.opt(key);
                if (value instanceof JSONObject || value instanceof JSONArray) continue;
                raw.addView(labelValue(key, String.valueOf(value)));
                shown++;
            }
            content.addView(raw, matchWrapBottom(14));
        }
    }

    private void showR26ColorPicker() {
        final String[] labels = {"Colore importato da Windows", "Verde Clinica", "Blu", "Petrolio", "Bordeaux", "Viola", "Arancio"};
        final String[] values = {"WINDOWS", "#178A72", "#2D6CA3", "#167C80", "#8A3549", "#71518E", "#B46827"};
        new AlertDialog.Builder(this).setTitle("Colore interfaccia").setItems(labels, (d, which) -> {
            String value = values[which];
            if ("WINDOWS".equals(value)) prefs.edit().remove("r26_theme_override").apply();
            else prefs.edit().putString("r26_theme_override", value).apply();
            loadR26ImportedUiSettings();
            getWindow().setStatusBarColor(GREEN_DARK);
            if (sessionAuthenticated) showMainUi(null);
        }).show();
    }

    private void showR26TimeoutPicker() {
        final int[] values = {5, 10, 15, 30, 60};
        final String[] labels = {"5 minuti", "10 minuti", "15 minuti", "30 minuti", "60 minuti"};
        new AlertDialog.Builder(this).setTitle("Timeout di sicurezza").setItems(labels, (d, which) -> {
            r26SessionTimeoutMinutes = values[which];
            prefs.edit().putInt("r26_timeout_override", r26SessionTimeoutMinutes).apply();
            r26LastInteractionAt = System.currentTimeMillis();
            scheduleR26TimeoutCheck();
            if ("Preferenze".equals(currentSection)) renderSection("Preferenze");
        }).show();
    }

    private void renderImportedRecordsSection(String titleText, String introText, JSONArray records, String emptyText) {
        LinearLayout intro = card();
        intro.addView(sectionHeader(titleText));
        intro.addView(text(introText, 13, MUTED, false));
        intro.addView(labelValue("Elementi", String.valueOf(records == null ? 0 : records.length())));
        content.addView(intro, matchWrapBottom(14));
        if (records == null || records.length() == 0) {
            LinearLayout empty = card();
            empty.addView(text(emptyText, 14, MUTED, false));
            content.addView(empty, matchWrapBottom(14));
            return;
        }
        renderImportedRecordCards(records, titleText);
    }

    private void renderImportedRecordCards(JSONArray records, String fallback) {
        int shown = Math.min(records.length(), 120);
        for (int i = 0; i < shown; i++) {
            JSONObject row = records.optJSONObject(i);
            if (row == null) continue;
            LinearLayout c = card();
            c.addView(text(R26SnapshotBridge.recordTitle(row, fallback), 16, TEXT, true));
            String sub = R26SnapshotBridge.recordSubtitle(row);
            if (!sub.isEmpty()) c.addView(text(sub, 13, GREEN_DARK, true));
            java.util.Iterator<String> keys = row.keys();
            int details = 0;
            while (keys.hasNext() && details < 8) {
                String key = keys.next();
                if (key.startsWith("_") || "id".equalsIgnoreCase(key) || "title".equalsIgnoreCase(key) || "name".equalsIgnoreCase(key)) continue;
                Object value = row.opt(key);
                if (value == null || value == JSONObject.NULL || value instanceof JSONObject || value instanceof JSONArray) continue;
                String textValue = String.valueOf(value).trim();
                if (textValue.isEmpty()) continue;
                c.addView(labelValue(key, textValue));
                details++;
            }
            content.addView(c, matchWrapBottom(10));
        }
    }

'''
s = s.replace(insert_marker, methods + insert_marker, 1)

# Visible release labels/version strings.
s = s.replace('Android R25 TEST', 'Android R26 QUASI DEFINITIVA')
s = s.replace('Aiuto R25', 'Aiuto R26')
s = s.replace('R25: struttura presente', 'R26: sezione collegata al Dossier sincronizzato')
s = s.replace('R25 mantiene lo stesso pacchetto Android', 'R26 mantiene lo stesso pacchetto Android')
s = s.replace('Installala sopra la R24', 'Installala sopra la R25')

MAIN.write_text(s, encoding='utf-8')

# Rotation must not recreate the authenticated Activity and force a new login.
m = MANIFEST.read_text(encoding='utf-8')
old_activity = '''        <activity
            android:name=".R6MainActivity"
            android:exported="true">'''
new_activity = '''        <activity
            android:name=".R6MainActivity"
            android:exported="true"
            android:screenOrientation="unspecified"
            android:configChanges="orientation|screenSize|keyboardHidden">'''
m = replace_once(m, old_activity, new_activity, 'rotation session preservation')
MANIFEST.write_text(m, encoding='utf-8')

# Version bump only; same package and same signing identity are preserved by the workflow.
g = GRADLE.read_text(encoding='utf-8')
g = replace_once(g, 'versionCode 25', 'versionCode 26', 'versionCode')
g = replace_once(g, "versionName '1.0.0-android-r25-test'", "versionName '1.0.0-android-r26-near-final'", 'versionName')
GRADLE.write_text(g, encoding='utf-8')

print('R26 near-final UI, sections, settings, timeout, rotation and health-card patch applied')
