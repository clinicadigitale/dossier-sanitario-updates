from pathlib import Path

BASE = Path('android-r3/app/src/main/java/it/dossiersanitario/clinicadigitale/beta')
MAIN = BASE / 'R6MainActivity.java'
EDITOR = BASE / 'DocumentEditorActivity.java'


def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit(f'R9 patch failed: missing {label}')
    return text.replace(old, new, 1)


def patch_main():
    s = MAIN.read_text(encoding='utf-8')

    s = replace_once(
        s,
        'import android.widget.Toast;\n\nimport org.json.JSONArray;',
        'import android.widget.Toast;\nimport android.text.InputType;\n\nimport org.json.JSONArray;',
        'InputType import'
    )
    s = replace_once(
        s,
        'import java.io.File;\nimport java.text.SimpleDateFormat;',
        'import java.io.BufferedInputStream;\nimport java.io.BufferedOutputStream;\nimport java.io.ByteArrayOutputStream;\nimport java.io.File;\nimport java.io.FileInputStream;\nimport java.io.FileOutputStream;\nimport java.io.InputStream;\nimport java.io.OutputStream;\nimport java.nio.charset.StandardCharsets;\nimport java.security.SecureRandom;\nimport java.text.SimpleDateFormat;',
        'backup java imports'
    )
    s = replace_once(
        s,
        'import java.util.Locale;\n',
        'import java.util.Locale;\nimport java.util.zip.ZipEntry;\nimport java.util.zip.ZipInputStream;\nimport java.util.zip.ZipOutputStream;\n\nimport javax.crypto.Cipher;\nimport javax.crypto.CipherInputStream;\nimport javax.crypto.CipherOutputStream;\nimport javax.crypto.SecretKey;\nimport javax.crypto.SecretKeyFactory;\nimport javax.crypto.spec.GCMParameterSpec;\nimport javax.crypto.spec.PBEKeySpec;\nimport javax.crypto.spec.SecretKeySpec;\n',
        'crypto imports'
    )

    s = replace_once(
        s,
        '    private static final int EDIT_DOCUMENT = 5103;\n',
        '    private static final int EDIT_DOCUMENT = 5103;\n'
        '    private static final int CREATE_BACKUP = 5201;\n'
        '    private static final int OPEN_BACKUP = 5202;\n',
        'backup request codes'
    )

    s = replace_once(
        s,
        '    private static final String PREF_EVENTS = "android_history_json";\n',
        '    private static final String PREF_EVENTS = "android_history_json"; // audit tecnico interno, non mostrato nella Cronologia clinica\n'
        '    private static final String PREF_CLINICAL_EVENTS = "android_clinical_events_json";\n'
        '    private static final String PREF_AGENDA = "android_agenda_json";\n',
        'clinical preference constants'
    )

    s = replace_once(
        s,
        '    private boolean pendingEditorNewCapture = false;\n',
        '    private boolean pendingEditorNewCapture = false;\n'
        '    private String pendingBackupPassword = null;\n'
        '    private Uri pendingRestoreUri = null;\n',
        'backup state'
    )

    s = replace_once(
        s,
        '            case "Medici e specialisti": renderMedici(); break;\n            case "Monitoraggio": renderMonitoraggio(); break;',
        '            case "Medici e specialisti": renderMedici(); break;\n            case "Agenda": renderAgenda(); break;\n            case "Monitoraggio": renderMonitoraggio(); break;',
        'agenda switch'
    )

    s = s.replace('case "Cronologia": return "Attività e modifiche rilevanti registrate nel Dossier locale.";',
                  'case "Cronologia": return "Eventi clinici del profilo: visite, esami, analisi, referti e terapie.";')

    start = s.find('    private void renderCronologia() {')
    end = s.find('    private LinearLayout dialogForm() {', start)
    if start < 0 or end < 0:
        raise SystemExit('R9 patch failed: chronology block not found')

    clinical = r'''    private void renderCronologia() {
        LinearLayout intro = card();
        intro.addView(sectionHeader("Cronologia clinica"));
        intro.addView(text("Qui compaiono solo eventi sanitari del profilo. Le modifiche tecniche dell'app non fanno parte della Cronologia clinica.", 13, MUTED, false));
        Button add = button("Aggiungi evento clinico");
        add.setOnClickListener(v -> showClinicalEventDialog(null));
        intro.addView(add, matchWrapTop(10));
        content.addView(intro, matchWrapBottom(14));

        JSONArray events = readArray(PREF_CLINICAL_EVENTS);
        if (events.length() == 0) {
            LinearLayout empty = card();
            empty.addView(text("Nessun evento clinico registrato.", 14, MUTED, false));
            content.addView(empty, matchWrapBottom(14));
            return;
        }

        for (int i = 0; i < events.length(); i++) {
            JSONObject e = events.optJSONObject(i);
            if (e == null) continue;
            long id = e.optLong("id", 0L);
            LinearLayout c = card();
            String type = e.optString("type", "Evento clinico").trim();
            String title = e.optString("title", "").trim();
            c.addView(text(type.isEmpty() ? "Evento clinico" : type, 13, GREEN_DARK, true));
            c.addView(text(title.isEmpty() ? "Evento clinico" : title, 17, TEXT, true));
            String date = e.optString("date", "").trim();
            String time = e.optString("time", "").trim();
            if (!date.isEmpty() || !time.isEmpty()) c.addView(labelValue("Quando", (date + " " + time).trim()));
            String notes = e.optString("notes", "").trim();
            if (!notes.isEmpty()) c.addView(labelValue("Note", notes));

            LinearLayout actions = new LinearLayout(this);
            actions.setOrientation(LinearLayout.HORIZONTAL);
            actions.setPadding(0, dp(9), 0, 0);
            Button edit = compactButton("Modifica");
            edit.setOnClickListener(v -> showClinicalEventDialog(e));
            actions.addView(edit, new LinearLayout.LayoutParams(0, dp(42), 1f));
            Button del = compactButton("Elimina");
            LinearLayout.LayoutParams ep = new LinearLayout.LayoutParams(0, dp(42), 1f);
            ep.setMargins(dp(7), 0, 0, 0);
            del.setOnClickListener(v -> confirmDeleteClinicalEvent(id));
            actions.addView(del, ep);
            c.addView(actions);
            content.addView(c, matchWrapBottom(10));
        }
    }

    private void showClinicalEventDialog(JSONObject existing) {
        LinearLayout form = dialogForm();
        EditText type = field("Tipo (Visita, Analisi, Esame, Referto, Terapia...)", existing == null ? "" : existing.optString("type", ""));
        EditText title = field("Descrizione evento", existing == null ? "" : existing.optString("title", ""));
        EditText date = field("Data (gg/mm/aaaa)", existing == null ? "" : existing.optString("date", ""));
        EditText time = field("Ora (hh:mm)", existing == null ? "" : existing.optString("time", ""));
        EditText notes = field("Note", existing == null ? "" : existing.optString("notes", ""));
        form.addView(type); form.addView(title); form.addView(date); form.addView(time); form.addView(notes);

        new AlertDialog.Builder(this)
                .setTitle(existing == null ? "Nuovo evento clinico" : "Modifica evento clinico")
                .setView(form)
                .setNegativeButton("Annulla", null)
                .setPositiveButton("Salva", (d, w) -> {
                    String t = clean(type);
                    String ttl = clean(title);
                    if (t.isEmpty() || ttl.isEmpty()) {
                        Toast.makeText(this, "Inserisci tipo e descrizione dell'evento", Toast.LENGTH_LONG).show();
                        return;
                    }
                    try {
                        long id = existing == null ? System.currentTimeMillis() : existing.optLong("id", System.currentTimeMillis());
                        JSONObject obj = new JSONObject();
                        obj.put("id", id);
                        obj.put("type", t);
                        obj.put("title", ttl);
                        obj.put("date", clean(date));
                        obj.put("time", clean(time));
                        obj.put("notes", clean(notes));
                        obj.put("updated", System.currentTimeMillis());
                        upsertClinicalEvent(obj);
                        renderSection("Cronologia");
                    } catch (Exception ex) {
                        Toast.makeText(this, "Salvataggio evento non riuscito", Toast.LENGTH_LONG).show();
                    }
                })
                .show();
    }

    private void upsertClinicalEvent(JSONObject object) throws Exception {
        JSONArray array = readArray(PREF_CLINICAL_EVENTS);
        long id = object.optLong("id", 0L);
        JSONArray next = new JSONArray();
        next.put(object);
        for (int i = 0; i < array.length(); i++) {
            JSONObject current = array.optJSONObject(i);
            if (current != null && current.optLong("id", -1L) != id) next.put(current);
        }
        saveArray(PREF_CLINICAL_EVENTS, next);
    }

    private void confirmDeleteClinicalEvent(long id) {
        new AlertDialog.Builder(this)
                .setTitle("Eliminare l'evento clinico?")
                .setMessage("L'evento verrà rimosso dalla Cronologia clinica.")
                .setNegativeButton("Annulla", null)
                .setPositiveButton("Elimina", (d, w) -> {
                    JSONArray array = readArray(PREF_CLINICAL_EVENTS);
                    for (int i = array.length() - 1; i >= 0; i--) {
                        JSONObject obj = array.optJSONObject(i);
                        if (obj != null && obj.optLong("id", -1L) == id) array.remove(i);
                    }
                    saveArray(PREF_CLINICAL_EVENTS, array);
                    renderSection("Cronologia");
                })
                .show();
    }

'''
    s = s[:start] + clinical + s[end:]

    latest_start = s.find('    private String latestEventSummary() {')
    latest_end = s.find('\n    private void renderMonitoraggio() {', latest_start)
    if latest_start < 0 or latest_end < 0:
        raise SystemExit('R9 patch failed: latest event function not found')
    latest = r'''    private String latestEventSummary() {
        JSONArray events = readArray(PREF_CLINICAL_EVENTS);
        JSONObject event = events.optJSONObject(0);
        if (event == null) return "Nessuno";
        String type = event.optString("type", "").trim();
        String title = event.optString("title", "").trim();
        String text = (type + (type.isEmpty() || title.isEmpty() ? "" : ": ") + title).trim();
        if (text.length() > 32) text = text.substring(0, 29) + "…";
        return text.isEmpty() ? "Nessuno" : text;
    }
'''
    s = s[:latest_start] + latest + s[latest_end:]

    agenda_marker = '    private void renderMonitoraggio() {'
    if agenda_marker not in s:
        raise SystemExit('R9 patch failed: agenda insertion point missing')
    agenda = r'''    private void renderAgenda() {
        LinearLayout intro = card();
        intro.addView(sectionHeader("Agenda"));
        intro.addView(text("Visite, esami e appuntamenti sanitari del profilo. Gli eventi salvati qui vengono riportati anche nella Cronologia clinica.", 13, MUTED, false));
        Button add = button("Aggiungi appuntamento");
        add.setOnClickListener(v -> showAgendaDialog(null));
        intro.addView(add, matchWrapTop(10));
        content.addView(intro, matchWrapBottom(14));

        JSONArray items = readArray(PREF_AGENDA);
        if (items.length() == 0) {
            LinearLayout empty = card();
            empty.addView(text("Nessun appuntamento sanitario registrato.", 14, MUTED, false));
            content.addView(empty, matchWrapBottom(14));
            return;
        }
        for (int i = 0; i < items.length(); i++) {
            JSONObject item = items.optJSONObject(i);
            if (item == null) continue;
            long id = item.optLong("id", 0L);
            LinearLayout c = card();
            String type = item.optString("type", "Visita").trim();
            c.addView(text(type.isEmpty() ? "Appuntamento" : type, 13, GREEN_DARK, true));
            c.addView(text(item.optString("title", "Appuntamento sanitario"), 17, TEXT, true));
            c.addView(labelValue("Quando", (item.optString("date", "") + " " + item.optString("time", "")).trim()));
            String notes = item.optString("notes", "").trim();
            if (!notes.isEmpty()) c.addView(labelValue("Note", notes));
            LinearLayout actions = new LinearLayout(this);
            actions.setOrientation(LinearLayout.HORIZONTAL);
            actions.setPadding(0, dp(9), 0, 0);
            Button edit = compactButton("Modifica");
            edit.setOnClickListener(v -> showAgendaDialog(item));
            actions.addView(edit, new LinearLayout.LayoutParams(0, dp(42), 1f));
            Button del = compactButton("Elimina");
            LinearLayout.LayoutParams ep = new LinearLayout.LayoutParams(0, dp(42), 1f);
            ep.setMargins(dp(7), 0, 0, 0);
            del.setOnClickListener(v -> confirmDeleteAgenda(id));
            actions.addView(del, ep);
            c.addView(actions);
            content.addView(c, matchWrapBottom(10));
        }
    }

    private void showAgendaDialog(JSONObject existing) {
        LinearLayout form = dialogForm();
        EditText type = field("Tipo (Visita, Esame, Analisi...)", existing == null ? "Visita" : existing.optString("type", "Visita"));
        EditText title = field("Descrizione", existing == null ? "" : existing.optString("title", ""));
        EditText date = field("Data (gg/mm/aaaa)", existing == null ? "" : existing.optString("date", ""));
        EditText time = field("Ora (hh:mm)", existing == null ? "" : existing.optString("time", ""));
        EditText notes = field("Note", existing == null ? "" : existing.optString("notes", ""));
        form.addView(type); form.addView(title); form.addView(date); form.addView(time); form.addView(notes);
        new AlertDialog.Builder(this)
                .setTitle(existing == null ? "Nuovo appuntamento" : "Modifica appuntamento")
                .setView(form)
                .setNegativeButton("Annulla", null)
                .setPositiveButton("Salva", (d, w) -> {
                    if (clean(title).isEmpty() || clean(date).isEmpty()) {
                        Toast.makeText(this, "Inserisci almeno descrizione e data", Toast.LENGTH_LONG).show();
                        return;
                    }
                    try {
                        long id = existing == null ? System.currentTimeMillis() : existing.optLong("id", System.currentTimeMillis());
                        JSONObject obj = new JSONObject();
                        obj.put("id", id);
                        obj.put("type", clean(type));
                        obj.put("title", clean(title));
                        obj.put("date", clean(date));
                        obj.put("time", clean(time));
                        obj.put("notes", clean(notes));
                        obj.put("updated", System.currentTimeMillis());
                        upsertRecord(PREF_AGENDA, obj);
                        JSONObject clinical = new JSONObject(obj.toString());
                        clinical.put("source", "agenda");
                        upsertClinicalEvent(clinical);
                        renderSection("Agenda");
                    } catch (Exception ex) {
                        Toast.makeText(this, "Salvataggio appuntamento non riuscito", Toast.LENGTH_LONG).show();
                    }
                })
                .show();
    }

    private void confirmDeleteAgenda(long id) {
        new AlertDialog.Builder(this)
                .setTitle("Eliminare l'appuntamento?")
                .setMessage("Verrà rimosso anche l'evento collegato dalla Cronologia clinica.")
                .setNegativeButton("Annulla", null)
                .setPositiveButton("Elimina", (d, w) -> {
                    JSONArray agenda = readArray(PREF_AGENDA);
                    for (int i = agenda.length() - 1; i >= 0; i--) {
                        JSONObject obj = agenda.optJSONObject(i);
                        if (obj != null && obj.optLong("id", -1L) == id) agenda.remove(i);
                    }
                    saveArray(PREF_AGENDA, agenda);
                    JSONArray clinical = readArray(PREF_CLINICAL_EVENTS);
                    for (int i = clinical.length() - 1; i >= 0; i--) {
                        JSONObject obj = clinical.optJSONObject(i);
                        if (obj != null && obj.optLong("id", -1L) == id && "agenda".equals(obj.optString("source", ""))) clinical.remove(i);
                    }
                    saveArray(PREF_CLINICAL_EVENTS, clinical);
                    renderSection("Agenda");
                })
                .show();
    }

'''
    s = s.replace(agenda_marker, agenda + agenda_marker, 1)

    bstart = s.find('    private void renderBackup() {')
    bend = s.find('    private void renderAiuto() {', bstart)
    if bstart < 0 or bend < 0:
        raise SystemExit('R9 patch failed: backup page block not found')
    backup_ui = r'''    private void renderBackup() {
        LinearLayout c = card();
        c.addView(sectionHeader("Backup cifrato"));
        c.addView(text("Crea un pacchetto cifrato del Dossier Android con dati del profilo, esenzioni, medici, Agenda, Cronologia clinica e documenti fotografici. Il file può essere salvato nella posizione scelta dal selettore Android.", 14, TEXT, false));
        c.addView(text("Il ripristino verifica prima il pacchetto e poi sostituisce i dati locali. La password non viene memorizzata nell'app.", 13, MUTED, false));
        Button create = button("Crea backup cifrato");
        create.setOnClickListener(v -> askBackupPassword());
        c.addView(create, matchWrapTop(12));
        Button restore = button("Ripristina da backup");
        restore.setOnClickListener(v -> chooseBackupToRestore());
        c.addView(restore, matchWrapTop(8));
        content.addView(c, matchWrapBottom(14));

        LinearLayout cloud = card();
        cloud.addView(sectionHeader("Sincronizzazione cloud"));
        cloud.addView(text("In questa fase verifichiamo prima che Android sappia creare e ricostruire autonomamente un backup completo e cifrato. Il collegamento diretto al cloud familiare verrà attivato solo dopo questo test di integrità.", 13, MUTED, false));
        content.addView(cloud, matchWrapBottom(14));
    }

    private void askBackupPassword() {
        LinearLayout form = dialogForm();
        EditText p1 = field("Password backup", "");
        EditText p2 = field("Ripeti password", "");
        p1.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD);
        p2.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD);
        form.addView(p1); form.addView(p2);
        new AlertDialog.Builder(this)
                .setTitle("Proteggi il backup")
                .setMessage("Usa almeno 8 caratteri. Senza questa password il backup non è ripristinabile.")
                .setView(form)
                .setNegativeButton("Annulla", null)
                .setPositiveButton("Continua", (d, w) -> {
                    String a = p1.getText().toString();
                    String b = p2.getText().toString();
                    if (a.length() < 8 || !a.equals(b)) {
                        Toast.makeText(this, "Le password devono coincidere e contenere almeno 8 caratteri", Toast.LENGTH_LONG).show();
                        return;
                    }
                    pendingBackupPassword = a;
                    Intent i = new Intent(Intent.ACTION_CREATE_DOCUMENT);
                    i.addCategory(Intent.CATEGORY_OPENABLE);
                    i.setType("application/octet-stream");
                    String stamp = new SimpleDateFormat("yyyyMMdd_HHmm", Locale.ITALY).format(new Date());
                    i.putExtra(Intent.EXTRA_TITLE, "ClinicaDigitale_backup_" + stamp + ".cdbackup");
                    startActivityForResult(i, CREATE_BACKUP);
                })
                .show();
    }

    private void chooseBackupToRestore() {
        Intent i = new Intent(Intent.ACTION_OPEN_DOCUMENT);
        i.addCategory(Intent.CATEGORY_OPENABLE);
        i.setType("*/*");
        startActivityForResult(i, OPEN_BACKUP);
    }

    private void askRestorePassword(Uri uri) {
        pendingRestoreUri = uri;
        EditText password = field("Password backup", "");
        password.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD);
        LinearLayout form = dialogForm();
        form.addView(password);
        new AlertDialog.Builder(this)
                .setTitle("Ripristina Dossier")
                .setMessage("Il ripristino sostituirà i dati Android locali dopo la verifica del backup.")
                .setView(form)
                .setNegativeButton("Annulla", (d, w) -> pendingRestoreUri = null)
                .setPositiveButton("Verifica e ripristina", (d, w) -> {
                    String p = password.getText().toString();
                    if (p.isEmpty()) return;
                    restoreEncryptedBackup(pendingRestoreUri, p);
                    pendingRestoreUri = null;
                })
                .show();
    }

    private SecretKey deriveBackupKey(char[] password, byte[] salt) throws Exception {
        PBEKeySpec spec = new PBEKeySpec(password, salt, 150000, 256);
        byte[] encoded = SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256").generateSecret(spec).getEncoded();
        spec.clearPassword();
        return new SecretKeySpec(encoded, "AES");
    }

    private JSONObject buildBackupManifest() throws Exception {
        JSONObject m = new JSONObject();
        m.put("schema", 1);
        m.put("created", System.currentTimeMillis());
        JSONObject profile = new JSONObject();
        String[] keys = {"profile_first_name", "profile_last_name", "profile_birth", "profile_address", "profile_zip", "profile_city", "profile_province", "test_value"};
        for (String key : keys) profile.put(key, prefs.getString(key, ""));
        profile.put("saved_at", prefs.getLong("saved_at", 0L));
        m.put("profile", profile);
        m.put("exemptions", readArray(PREF_EXEMPTIONS));
        m.put("doctors", readArray(PREF_DOCTORS));
        m.put("agenda", readArray(PREF_AGENDA));
        m.put("clinical", readArray(PREF_CLINICAL_EVENTS));
        return m;
    }

    private void writeEncryptedBackup(Uri uri, String password) {
        if (uri == null || password == null) return;
        File zip = new File(getCacheDir(), "clinica_backup_plain.zip");
        try {
            try (ZipOutputStream zos = new ZipOutputStream(new BufferedOutputStream(new FileOutputStream(zip)))) {
                ZipEntry manifest = new ZipEntry("manifest.json");
                zos.putNextEntry(manifest);
                zos.write(buildBackupManifest().toString().getBytes(StandardCharsets.UTF_8));
                zos.closeEntry();
                File[] docs = privatePhotos();
                if (docs != null) {
                    byte[] buffer = new byte[64 * 1024];
                    for (File doc : docs) {
                        ZipEntry e = new ZipEntry("documents/" + doc.getName());
                        zos.putNextEntry(e);
                        try (InputStream in = new BufferedInputStream(new FileInputStream(doc))) {
                            int n;
                            while ((n = in.read(buffer)) > 0) zos.write(buffer, 0, n);
                        }
                        zos.closeEntry();
                    }
                }
            }

            byte[] salt = new byte[16];
            byte[] iv = new byte[12];
            SecureRandom rng = new SecureRandom();
            rng.nextBytes(salt); rng.nextBytes(iv);
            SecretKey key = deriveBackupKey(password.toCharArray(), salt);
            Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
            cipher.init(Cipher.ENCRYPT_MODE, key, new GCMParameterSpec(128, iv));
            try (OutputStream raw = new BufferedOutputStream(getContentResolver().openOutputStream(uri, "w"))) {
                raw.write("CDBACKUP1".getBytes(StandardCharsets.US_ASCII));
                raw.write(salt);
                raw.write(iv);
                try (CipherOutputStream cos = new CipherOutputStream(raw, cipher);
                     InputStream in = new BufferedInputStream(new FileInputStream(zip))) {
                    byte[] buffer = new byte[64 * 1024];
                    int n;
                    while ((n = in.read(buffer)) > 0) cos.write(buffer, 0, n);
                }
            }
            Toast.makeText(this, "Backup cifrato creato e verificabile", Toast.LENGTH_LONG).show();
        } catch (Exception e) {
            Toast.makeText(this, "Creazione backup non riuscita", Toast.LENGTH_LONG).show();
        } finally {
            pendingBackupPassword = null;
            zip.delete();
        }
    }

    private void restoreEncryptedBackup(Uri uri, String password) {
        if (uri == null) return;
        File stage = new File(getCacheDir(), "restore_stage");
        deleteRecursively(stage);
        stage.mkdirs();
        try (InputStream raw = new BufferedInputStream(getContentResolver().openInputStream(uri))) {
            byte[] magic = readExact(raw, 9);
            if (!"CDBACKUP1".equals(new String(magic, StandardCharsets.US_ASCII))) throw new Exception("bad magic");
            byte[] salt = readExact(raw, 16);
            byte[] iv = readExact(raw, 12);
            SecretKey key = deriveBackupKey(password.toCharArray(), salt);
            Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
            cipher.init(Cipher.DECRYPT_MODE, key, new GCMParameterSpec(128, iv));

            try (ZipInputStream zis = new ZipInputStream(new CipherInputStream(raw, cipher))) {
                ZipEntry entry;
                byte[] buffer = new byte[64 * 1024];
                while ((entry = zis.getNextEntry()) != null) {
                    File out = new File(stage, entry.getName());
                    String root = stage.getCanonicalPath() + File.separator;
                    if (!out.getCanonicalPath().startsWith(root)) throw new Exception("invalid entry");
                    if (entry.isDirectory()) { out.mkdirs(); continue; }
                    File parent = out.getParentFile();
                    if (parent != null) parent.mkdirs();
                    try (OutputStream os = new BufferedOutputStream(new FileOutputStream(out))) {
                        int n;
                        while ((n = zis.read(buffer)) > 0) os.write(buffer, 0, n);
                    }
                    zis.closeEntry();
                }
            }

            File manifestFile = new File(stage, "manifest.json");
            if (!manifestFile.isFile()) throw new Exception("manifest missing");
            JSONObject manifest = new JSONObject(new String(readAll(manifestFile), StandardCharsets.UTF_8));
            if (manifest.optInt("schema", -1) != 1) throw new Exception("unsupported schema");
            applyRestoredManifest(manifest, new File(stage, "documents"));
            profileName.setText(profileDisplayName());
            Toast.makeText(this, "Backup verificato e Dossier ripristinato", Toast.LENGTH_LONG).show();
            renderSection("Backup");
        } catch (Exception e) {
            Toast.makeText(this, "Backup non valido, password errata o file danneggiato", Toast.LENGTH_LONG).show();
        } finally {
            deleteRecursively(stage);
        }
    }

    private void applyRestoredManifest(JSONObject m, File stagedDocs) throws Exception {
        JSONObject profile = m.getJSONObject("profile");
        android.content.SharedPreferences.Editor ed = prefs.edit();
        String[] keys = {"profile_first_name", "profile_last_name", "profile_birth", "profile_address", "profile_zip", "profile_city", "profile_province", "test_value"};
        for (String key : keys) ed.putString(key, profile.optString(key, ""));
        ed.putLong("saved_at", profile.optLong("saved_at", 0L));
        ed.putString(PREF_EXEMPTIONS, m.optJSONArray("exemptions") == null ? "[]" : m.optJSONArray("exemptions").toString());
        ed.putString(PREF_DOCTORS, m.optJSONArray("doctors") == null ? "[]" : m.optJSONArray("doctors").toString());
        ed.putString(PREF_AGENDA, m.optJSONArray("agenda") == null ? "[]" : m.optJSONArray("agenda").toString());
        ed.putString(PREF_CLINICAL_EVENTS, m.optJSONArray("clinical") == null ? "[]" : m.optJSONArray("clinical").toString());
        ed.apply();

        File target = privateDocumentsDir();
        File[] old = target.listFiles();
        if (old != null) for (File f : old) f.delete();
        File[] incoming = stagedDocs.listFiles();
        if (incoming != null) {
            for (File f : incoming) {
                if (!f.getName().startsWith("referto_foto_") || !f.getName().endsWith(".jpg")) continue;
                copyFile(f, new File(target, f.getName()));
            }
        }
    }

    private static byte[] readExact(InputStream in, int count) throws Exception {
        byte[] out = new byte[count];
        int off = 0;
        while (off < count) {
            int n = in.read(out, off, count - off);
            if (n < 0) throw new Exception("unexpected eof");
            off += n;
        }
        return out;
    }

    private static byte[] readAll(File file) throws Exception {
        try (InputStream in = new FileInputStream(file); ByteArrayOutputStream out = new ByteArrayOutputStream()) {
            byte[] buffer = new byte[32 * 1024];
            int n;
            while ((n = in.read(buffer)) > 0) out.write(buffer, 0, n);
            return out.toByteArray();
        }
    }

    private static void copyFile(File src, File dst) throws Exception {
        try (InputStream in = new BufferedInputStream(new FileInputStream(src)); OutputStream out = new BufferedOutputStream(new FileOutputStream(dst))) {
            byte[] buffer = new byte[64 * 1024];
            int n;
            while ((n = in.read(buffer)) > 0) out.write(buffer, 0, n);
        }
    }

    private static void deleteRecursively(File f) {
        if (f == null || !f.exists()) return;
        if (f.isDirectory()) {
            File[] children = f.listFiles();
            if (children != null) for (File c : children) deleteRecursively(c);
        }
        f.delete();
    }

'''
    s = s[:bstart] + backup_ui + s[bend:]

    result_marker = '        if (requestCode == CAMERA_CAPTURE) {'
    if result_marker not in s:
        raise SystemExit('R9 patch failed: activity result marker missing')
    backup_results = r'''        if (requestCode == CREATE_BACKUP) {
            if (resultCode == RESULT_OK && data != null && data.getData() != null && pendingBackupPassword != null) {
                writeEncryptedBackup(data.getData(), pendingBackupPassword);
            } else {
                pendingBackupPassword = null;
            }
            return;
        }

        if (requestCode == OPEN_BACKUP) {
            if (resultCode == RESULT_OK && data != null && data.getData() != null) askRestorePassword(data.getData());
            return;
        }

'''
    s = s.replace(result_marker, backup_results + result_marker, 1)

    visible = {
        'Android R8 TEST': 'Android R9 TEST',
        'Aiuto R8': 'Aiuto R9',
        'R8: struttura presente': 'R9: struttura presente',
        'R8 mantiene lo stesso pacchetto Android': 'R9 mantiene lo stesso pacchetto Android',
        'Installala sopra la R7': 'Installala sopra la R8',
        'Importazione file non ancora attiva nella R8': 'Importazione file non ancora attiva nella R9'
    }
    for old, new in visible.items():
        s = s.replace(old, new)

    MAIN.write_text(s, encoding='utf-8')


def patch_editor():
    s = EDITOR.read_text(encoding='utf-8')

    start = s.find('    private boolean autoDetectEdges(boolean notify) {')
    end = s.find('    private static double maxRightAngleCosine(PointF[] p) {', start)
    if start < 0 or end < 0:
        raise SystemExit('R9 patch failed: edge detector not found')

    detector = r'''    private boolean autoDetectEdges(boolean notify) {
        if (!openCvReady) {
            if (notify) Toast.makeText(this, "Rilevamento automatico non disponibile", Toast.LENGTH_SHORT).show();
            return false;
        }
        Mat src = new Mat();
        Mat work = new Mat();
        Mat gray = new Mat();
        Mat contrast = new Mat();
        Mat smooth = new Mat();
        Mat canny = new Mat();
        Mat adaptiveLight = new Mat();
        Mat adaptiveDark = new Mat();
        Mat otsuLight = new Mat();
        Mat otsuDark = new Mat();
        CLAHE clahe = null;
        try {
            Utils.bitmapToMat(currentBitmap, src);
            double scale = 1.0;
            int maxSide = Math.max(src.cols(), src.rows());
            if (maxSide > 1600) scale = 1600.0 / maxSide;
            if (scale < 1.0) Imgproc.resize(src, work, new Size(), scale, scale, Imgproc.INTER_AREA); else src.copyTo(work);
            Imgproc.cvtColor(work, gray, Imgproc.COLOR_RGBA2GRAY);
            clahe = Imgproc.createCLAHE(2.5, new Size(8, 8));
            clahe.apply(gray, contrast);
            Imgproc.bilateralFilter(contrast, smooth, 7, 45, 45);
            Imgproc.Canny(smooth, canny, 35, 115);
            Imgproc.adaptiveThreshold(smooth, adaptiveLight, 255, Imgproc.ADAPTIVE_THRESH_GAUSSIAN_C, Imgproc.THRESH_BINARY, 41, 7);
            Core.bitwise_not(adaptiveLight, adaptiveDark);
            Imgproc.threshold(smooth, otsuLight, 0, 255, Imgproc.THRESH_BINARY | Imgproc.THRESH_OTSU);
            Core.bitwise_not(otsuLight, otsuDark);

            Mat[] masks = {canny, adaptiveLight, adaptiveDark, otsuLight, otsuDark};
            Point[] best = null;
            double bestScore = -1e9;
            double imageArea = (double) work.cols() * work.rows();
            double diag = Math.sqrt(work.cols() * (double) work.cols() + work.rows() * (double) work.rows());

            for (Mat baseMask : masks) {
                Mat mask = baseMask.clone();
                Mat kernel = Imgproc.getStructuringElement(Imgproc.MORPH_RECT, new Size(5, 5));
                Imgproc.morphologyEx(mask, mask, Imgproc.MORPH_CLOSE, kernel);
                Imgproc.morphologyEx(mask, mask, Imgproc.MORPH_CLOSE, kernel);
                Mat hierarchy = new Mat();
                List<MatOfPoint> contours = new ArrayList<>();
                Imgproc.findContours(mask, contours, hierarchy, Imgproc.RETR_LIST, Imgproc.CHAIN_APPROX_SIMPLE);

                for (MatOfPoint contour : contours) {
                    double area = Math.abs(Imgproc.contourArea(contour));
                    double ratio = area / imageArea;
                    if (ratio < 0.035 || ratio > 0.985) { contour.release(); continue; }
                    MatOfPoint2f curve = new MatOfPoint2f(contour.toArray());
                    double perimeter = Imgproc.arcLength(curve, true);
                    double[] eps = {0.012, 0.018, 0.025, 0.035, 0.050, 0.070};
                    for (double e : eps) {
                        MatOfPoint2f approx = new MatOfPoint2f();
                        Imgproc.approxPolyDP(curve, approx, perimeter * e, true);
                        Point[] pts = approx.toArray();
                        if (pts.length == 4) {
                            MatOfPoint quad = new MatOfPoint(pts);
                            if (Imgproc.isContourConvex(quad)) {
                                double qArea = Math.abs(Imgproc.contourArea(quad));
                                double qRatio = qArea / imageArea;
                                PointF[] ordered = orderCorners(pts);
                                double anglePenalty = Math.min(1.0, maxRightAngleCosine(ordered));
                                double cx = 0, cy = 0;
                                for (Point p : pts) { cx += p.x; cy += p.y; }
                                cx /= 4.0; cy /= 4.0;
                                double center = Math.sqrt((cx-work.cols()/2.0)*(cx-work.cols()/2.0) + (cy-work.rows()/2.0)*(cy-work.rows()/2.0)) / Math.max(1.0, diag/2.0);
                                center = Math.min(1.0, center);
                                double score = qRatio * 8.0 + (1.0-anglePenalty) * 2.0 + (1.0-center) * 0.8;
                                if (qRatio >= 0.10 && qRatio <= 0.94) score += 0.8;
                                if (score > bestScore) { bestScore = score; best = pts.clone(); }
                            }
                            quad.release();
                        }
                        approx.release();
                    }
                    if (best == null) {
                        RotatedRect rr = Imgproc.minAreaRect(curve);
                        double rectArea = Math.abs(rr.size.width * rr.size.height);
                        double rectRatio = rectArea / imageArea;
                        if (rectRatio >= 0.08 && rectRatio <= 0.96 && rectArea > 1.0) {
                            double fill = Math.min(1.0, area / rectArea);
                            double center = Math.sqrt((rr.center.x-work.cols()/2.0)*(rr.center.x-work.cols()/2.0) + (rr.center.y-work.rows()/2.0)*(rr.center.y-work.rows()/2.0)) / Math.max(1.0, diag/2.0);
                            double score = rectRatio * 4.0 + fill * 1.8 + (1.0-Math.min(1.0, center)) * 0.5;
                            if (score > bestScore && fill > 0.45) {
                                Point[] rect = new Point[4]; rr.points(rect); best = rect; bestScore = score;
                            }
                        }
                    }
                    curve.release();
                    contour.release();
                }
                hierarchy.release(); kernel.release(); mask.release();
            }

            if (best != null) {
                PointF[] ordered = orderCorners(best);
                float inv = (float)(1.0 / scale);
                for (PointF p : ordered) {
                    p.x = Math.max(0, Math.min(currentBitmap.getWidth()-1, p.x * inv));
                    p.y = Math.max(0, Math.min(currentBitmap.getHeight()-1, p.y * inv));
                }
                documentView.setCorners(ordered);
                status.setText("Bordi individuati. Controlla i quattro punti verdi prima di applicare Prospettiva.");
                if (notify) Toast.makeText(this, "Bordi individuati", Toast.LENGTH_SHORT).show();
                return true;
            }
            documentView.resetCorners();
            status.setText("Bordi non riconosciuti automaticamente. Puoi comunque posizionare i quattro punti verdi.");
            if (notify) Toast.makeText(this, "Bordi non riconosciuti", Toast.LENGTH_LONG).show();
            return false;
        } catch (Exception e) {
            documentView.resetCorners();
            status.setText("Rilevamento automatico non riuscito. Usa i quattro punti verdi.");
            return false;
        } finally {
            if (clahe != null) clahe.clear();
            src.release(); work.release(); gray.release(); contrast.release(); smooth.release(); canny.release();
            adaptiveLight.release(); adaptiveDark.release(); otsuLight.release(); otsuDark.release();
        }
    }

'''
    s = s[:start] + detector + s[end:]

    s = s.replace('Imgproc.createCLAHE(4.2, new Size(8, 8))', 'Imgproc.createCLAHE(3.2, new Size(8, 8))')
    s = s.replace('Core.addWeighted(enhancedRgb, 1.80, blur, -0.80, 0, sharp);', 'Core.addWeighted(enhancedRgb, 1.62, blur, -0.62, 0, sharp);')
    s = s.replace('sharp.convertTo(sharp, -1, 1.10, 5);', 'sharp.convertTo(sharp, -1, 1.04, 2);')
    s = s.replace('Contrasto, illuminazione e nitidezza del documento migliorati.', 'Leggibilità migliorata con intervento moderato.')

    bw_start = s.find('    private void blackWhiteDocument() {')
    bw_end = s.find('    private void replaceCurrent(Bitmap next, boolean resetCorners) {', bw_start)
    if bw_start < 0 or bw_end < 0:
        raise SystemExit('R9 patch failed: black/white function not found')
    bw = r'''    private void blackWhiteDocument() {
        if (!openCvReady) {
            Toast.makeText(this, "Bianco e nero non disponibile", Toast.LENGTH_SHORT).show();
            return;
        }
        Mat src = new Mat();
        Mat gray = new Mat();
        Mat contrast = new Mat();
        Mat blur = new Mat();
        Mat sharp = new Mat();
        Mat out = new Mat();
        CLAHE clahe = null;
        try {
            Utils.bitmapToMat(currentBitmap, src);
            Imgproc.cvtColor(src, gray, Imgproc.COLOR_RGBA2GRAY);
            clahe = Imgproc.createCLAHE(1.8, new Size(8, 8));
            clahe.apply(gray, contrast);
            Imgproc.GaussianBlur(contrast, blur, new Size(0, 0), 1.2);
            Core.addWeighted(contrast, 1.28, blur, -0.28, 0, sharp);
            Imgproc.cvtColor(sharp, out, Imgproc.COLOR_GRAY2RGBA);
            Bitmap result = Bitmap.createBitmap(out.cols(), out.rows(), Bitmap.Config.ARGB_8888);
            Utils.matToBitmap(out, result);
            replaceCurrent(result, false);
            status.setText("Bianco e nero leggibile applicato senza soglia aggressiva.");
        } catch (Exception e) {
            Toast.makeText(this, "Conversione non riuscita", Toast.LENGTH_SHORT).show();
        } finally {
            if (clahe != null) clahe.clear();
            src.release(); gray.release(); contrast.release(); blur.release(); sharp.release(); out.release();
        }
    }

'''
    s = s[:bw_start] + bw + s[bw_end:]

    EDITOR.write_text(s, encoding='utf-8')


patch_main()
patch_editor()
print('Android R9 patch applied successfully')
