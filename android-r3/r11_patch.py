from pathlib import Path

BASE = Path('android-r3/app/src/main/java/it/dossiersanitario/clinicadigitale/beta')
MAIN = BASE / 'R6MainActivity.java'
EDITOR = BASE / 'DocumentEditorActivity.java'


def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit(f'R11 patch failed: missing {label}')
    return text.replace(old, new, 1)


def patch_main():
    s = MAIN.read_text(encoding='utf-8')

    s = replace_once(
        s,
        '    private static final int OPEN_BACKUP = 5202;\n',
        '    private static final int OPEN_BACKUP = 5202;\n'
        '    private static final int IMPORT_AGENDA_DOCUMENT = 5301;\n',
        'agenda import request code'
    )

    s = replace_once(
        s,
        '    private static final String PREF_AGENDA = "android_agenda_json";\n',
        '    private static final String PREF_AGENDA = "android_agenda_json";\n'
        '    private static final String PREF_AGENDA_ALERTS = "android_agenda_default_alerts";\n',
        'agenda alert preference'
    )

    s = replace_once(
        s,
        '            case "Agenda": renderAgenda(); break;\n            case "Monitoraggio": renderMonitoraggio(); break;',
        '            case "Agenda": renderAgenda(); break;\n            case "Preferenze": renderPreferenze(); break;\n            case "Monitoraggio": renderMonitoraggio(); break;',
        'preferences switch'
    )

    old_intro = '''        Button add = button("Aggiungi appuntamento");\n        add.setOnClickListener(v -> showAgendaDialog(null));\n        intro.addView(add, matchWrapTop(10));\n        content.addView(intro, matchWrapBottom(14));'''
    new_intro = '''        Button add = button("Aggiungi appuntamento");\n        add.setOnClickListener(v -> showAgendaDialog(null));\n        intro.addView(add, matchWrapTop(10));\n        Button importBooking = button("Importa prenotazione da PDF / foto / scansione");\n        importBooking.setOnClickListener(v -> chooseAgendaImport());\n        intro.addView(importBooking, matchWrapTop(8));\n        content.addView(intro, matchWrapBottom(14));'''
    s = replace_once(s, old_intro, new_intro, 'agenda import button')

    card_start = s.find('    private LinearLayout buildAgendaCard(JSONObject item) {')
    card_end = s.find('    private void addAgendaEmptyState() {', card_start)
    if card_start < 0 or card_end < 0:
        raise SystemExit('R11 patch failed: agenda card block not found')

    card = r'''    private LinearLayout buildAgendaCard(JSONObject item) {
        long id = item.optLong("id", 0L);
        LinearLayout c = card();
        c.setTag(Long.valueOf(id));
        String type = item.optString("type", "Visita").trim();
        c.addView(text(type.isEmpty() ? "Appuntamento" : type, 13, GREEN_DARK, true));
        c.addView(text(item.optString("title", "Appuntamento sanitario"), 17, TEXT, true));
        c.addView(labelValue("Quando", (item.optString("date", "") + " " + item.optString("time", "")).trim()));
        String location = item.optString("location", "").trim();
        if (!location.isEmpty()) c.addView(labelValue("Dove presentarsi", location));
        String alerts = item.optString("alerts", prefs.getString(PREF_AGENDA_ALERTS, "1440"));
        String alertsText = formatAgendaAlerts(alerts);
        if (!alertsText.isEmpty()) c.addView(labelValue("Avvisi", alertsText));
        if (item.optBoolean("imported", false)) c.addView(text("Prenotazione importata", 12, GREEN_DARK, true));
        if (item.optBoolean("duplicate_hold", false)) c.addView(text("Possibile duplicato · sincronizzazione esterna sospesa fino alla scelta", 12, Color.rgb(155, 86, 0), true));
        String notes = item.optString("notes", "").trim();
        if (!notes.isEmpty()) c.addView(labelValue("Note", notes));
        String sourceUri = item.optString("source_uri", "").trim();
        if (!sourceUri.isEmpty()) {
            Button original = compactButton("Apri file originale");
            original.setOnClickListener(v -> openAgendaOriginal(item));
            c.addView(original, matchWrapTop(8));
        }
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
        return c;
    }

'''
    s = s[:card_start] + card + s[card_end:]

    dialog_start = s.find('    private void showAgendaDialog(JSONObject existing) {')
    dialog_end = s.find('    private void confirmDeleteAgenda(long id) {', dialog_start)
    if dialog_start < 0 or dialog_end < 0:
        raise SystemExit('R11 patch failed: agenda dialog block not found')

    dialog = r'''    private void showAgendaDialog(JSONObject existing) {
        final JSONObject seed = existing == null ? new JSONObject() : existing;
        final boolean isNew = existing == null || existing.optLong("id", 0L) == 0L;
        LinearLayout form = dialogForm();

        android.widget.AutoCompleteTextView type = new android.widget.AutoCompleteTextView(this);
        type.setHint("Tipo");
        type.setText(seed.optString("type", "Visita"));
        type.setTextSize(15);
        type.setTextColor(TEXT);
        type.setHintTextColor(MUTED);
        type.setSingleLine(true);
        type.setPadding(dp(12), dp(10), dp(12), dp(10));
        type.setMinHeight(dp(52));
        type.setBackground(roundRect(Color.WHITE, BORDER, 10));
        String[] agendaTypes = {"Visita", "Prenotazione visita", "Esame", "Prenotazione esami", "Controllo", "Richiamo", "Rinnovo esenzione", "Piano terapeutico", "Ricetta", "Richiesta impegnativa medico curante", "Documento sanitario", "Telefonare", "Altro"};
        android.widget.ArrayAdapter<String> typeAdapter = new android.widget.ArrayAdapter<>(this, android.R.layout.simple_dropdown_item_1line, agendaTypes);
        type.setAdapter(typeAdapter);
        type.setThreshold(0);
        type.setOnClickListener(v -> type.showDropDown());
        type.setOnFocusChangeListener((v, has) -> { if (has) type.showDropDown(); });

        EditText title = field("Titolo / descrizione", seed.optString("title", ""));
        EditText date = field("Data (gg/mm/aaaa)", seed.optString("date", ""));
        EditText time = field("Ora (hh:mm)", seed.optString("time", ""));
        EditText location = field("Luogo / dove presentarsi", seed.optString("location", ""));
        EditText notes = field("Note e indicazioni", seed.optString("notes", ""));

        Button pickDate = compactButton("Scegli data dal calendario");
        pickDate.setOnClickListener(v -> showAgendaDatePicker(date));
        Button pickTime = compactButton("Scegli ora");
        pickTime.setOnClickListener(v -> showAgendaTimePicker(time));
        final boolean[] datePrompted = {false};
        final boolean[] timePrompted = {false};
        date.setOnFocusChangeListener((v, has) -> {
            if (has && !datePrompted[0]) { datePrompted[0] = true; showAgendaDatePicker(date); }
        });
        time.setOnFocusChangeListener((v, has) -> {
            if (has && !timePrompted[0]) { timePrompted[0] = true; showAgendaTimePicker(time); }
        });

        form.addView(type, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        form.addView(title); form.addView(date); form.addView(pickDate); form.addView(time); form.addView(pickTime); form.addView(location); form.addView(notes);

        TextView alertTitle = sectionHeaderWithTop("Avvisi", 14);
        form.addView(alertTitle);
        form.addView(text("Usa i valori predefiniti delle Preferenze oppure modificali solo per questo appuntamento. Massimo 5 avvisi.", 12, MUTED, false));
        final int[] alertValues = agendaAlertValues();
        final String[] alertLabels = agendaAlertLabels();
        final android.widget.CheckBox[] alertChecks = new android.widget.CheckBox[alertValues.length];
        String initialAlerts = seed.has("alerts") ? seed.optString("alerts", "") : prefs.getString(PREF_AGENDA_ALERTS, "1440");
        LinearLayout alertBox = new LinearLayout(this);
        alertBox.setOrientation(LinearLayout.VERTICAL);
        for (int i = 0; i < alertValues.length; i++) {
            final int idx = i;
            android.widget.CheckBox cb = new android.widget.CheckBox(this);
            cb.setText(alertLabels[i]);
            cb.setTextColor(TEXT);
            cb.setChecked(csvHasInt(initialAlerts, alertValues[i]));
            cb.setOnCheckedChangeListener((button, checked) -> {
                if (checked && countChecked(alertChecks) > 5) {
                    button.setChecked(false);
                    Toast.makeText(this, "Puoi impostare al massimo 5 avvisi", Toast.LENGTH_SHORT).show();
                }
            });
            alertChecks[idx] = cb;
            alertBox.addView(cb);
        }
        form.addView(alertBox);

        new AlertDialog.Builder(this)
                .setTitle(isNew ? (seed.optBoolean("imported", false) ? "Controlla prenotazione importata" : "Nuovo appuntamento") : "Modifica appuntamento")
                .setView(form)
                .setNegativeButton("Annulla", null)
                .setPositiveButton("Salva", (d, w) -> {
                    if (clean(title).isEmpty() || clean(date).isEmpty()) {
                        Toast.makeText(this, "Inserisci almeno descrizione e data", Toast.LENGTH_LONG).show();
                        return;
                    }
                    try {
                        long id = isNew ? System.currentTimeMillis() : seed.optLong("id", System.currentTimeMillis());
                        JSONObject obj = new JSONObject();
                        obj.put("id", id);
                        obj.put("type", clean(type));
                        obj.put("title", clean(title));
                        obj.put("date", clean(date));
                        obj.put("time", clean(time));
                        obj.put("location", clean(location));
                        obj.put("notes", clean(notes));
                        obj.put("alerts", checkedAlertsCsv(alertChecks, alertValues));
                        obj.put("updated", System.currentTimeMillis());
                        if (seed.has("source_uri")) obj.put("source_uri", seed.optString("source_uri", ""));
                        if (seed.has("source_mime")) obj.put("source_mime", seed.optString("source_mime", ""));
                        if (seed.optBoolean("imported", false)) obj.put("imported", true);
                        copySyncLinkFields(seed, obj);

                        upsertRecord(PREF_AGENDA, obj);
                        refreshAgendaCard(obj);
                        mirrorAgendaToClinicalAsync(obj);

                        if (isNew) {
                            JSONObject duplicate = findSimilarAgendaItem(obj);
                            if (duplicate != null) {
                                obj.put("duplicate_hold", true);
                                upsertRecord(PREF_AGENDA, obj);
                                refreshAgendaCard(obj);
                                showDuplicateAgendaDialog(obj, duplicate);
                            }
                        }
                        Toast.makeText(this, "Appuntamento salvato", Toast.LENGTH_SHORT).show();
                    } catch (Exception ex) {
                        Toast.makeText(this, "Salvataggio appuntamento non riuscito", Toast.LENGTH_LONG).show();
                    }
                })
                .show();
    }

    private void showAgendaDatePicker(EditText target) {
        java.util.Calendar cal = java.util.Calendar.getInstance();
        String current = target.getText().toString().trim();
        if (!current.isEmpty()) {
            try {
                Date parsed = new SimpleDateFormat("dd/MM/yyyy", Locale.ITALY).parse(current);
                if (parsed != null) cal.setTime(parsed);
            } catch (Exception ignored) {}
        }
        new android.app.DatePickerDialog(this, (view, y, m, d) -> target.setText(String.format(Locale.ITALY, "%02d/%02d/%04d", d, m + 1, y)),
                cal.get(java.util.Calendar.YEAR), cal.get(java.util.Calendar.MONTH), cal.get(java.util.Calendar.DAY_OF_MONTH)).show();
    }

    private void showAgendaTimePicker(EditText target) {
        java.util.Calendar cal = java.util.Calendar.getInstance();
        int hour = cal.get(java.util.Calendar.HOUR_OF_DAY);
        int minute = cal.get(java.util.Calendar.MINUTE);
        String current = target.getText().toString().trim();
        if (current.matches("\\d{1,2}:\\d{2}")) {
            try {
                String[] p = current.split(":");
                hour = Integer.parseInt(p[0]); minute = Integer.parseInt(p[1]);
            } catch (Exception ignored) {}
        }
        new android.app.TimePickerDialog(this, (view, h, m) -> target.setText(String.format(Locale.ITALY, "%02d:%02d", h, m)), hour, minute, true).show();
    }

    private int[] agendaAlertValues() { return new int[]{40320, 20160, 10080, 2880, 1440, 120, 90, 60, 30}; }
    private String[] agendaAlertLabels() { return new String[]{"4 settimane prima", "2 settimane prima", "1 settimana prima", "2 giorni prima", "1 giorno prima", "2 ore prima", "1 ora e 30 minuti prima", "1 ora prima", "30 minuti prima"}; }

    private boolean csvHasInt(String csv, int value) {
        if (csv == null || csv.trim().isEmpty()) return false;
        for (String p : csv.split(",")) if (String.valueOf(value).equals(p.trim())) return true;
        return false;
    }

    private int countChecked(android.widget.CheckBox[] checks) {
        int n = 0;
        if (checks != null) for (android.widget.CheckBox c : checks) if (c != null && c.isChecked()) n++;
        return n;
    }

    private String checkedAlertsCsv(android.widget.CheckBox[] checks, int[] values) {
        StringBuilder out = new StringBuilder();
        for (int i = 0; i < checks.length; i++) {
            if (checks[i] != null && checks[i].isChecked()) {
                if (out.length() > 0) out.append(',');
                out.append(values[i]);
            }
        }
        return out.toString();
    }

    private String formatAgendaAlerts(String csv) {
        int[] values = agendaAlertValues();
        String[] labels = agendaAlertLabels();
        StringBuilder out = new StringBuilder();
        for (int i = 0; i < values.length; i++) {
            if (csvHasInt(csv, values[i])) {
                if (out.length() > 0) out.append(", ");
                out.append(labels[i]);
            }
        }
        return out.toString();
    }

    private void copySyncLinkFields(JSONObject from, JSONObject to) throws Exception {
        String[] keys = {"google_event_id", "google_calendar_id", "google_sync_state", "google_updated"};
        for (String key : keys) if (from.has(key)) to.put(key, from.opt(key));
    }

    private void chooseAgendaImport() {
        Intent i = new Intent(Intent.ACTION_OPEN_DOCUMENT);
        i.addCategory(Intent.CATEGORY_OPENABLE);
        i.setType("*/*");
        i.putExtra(Intent.EXTRA_MIME_TYPES, new String[]{"application/pdf", "image/jpeg", "image/png", "image/webp"});
        startActivityForResult(i, IMPORT_AGENDA_DOCUMENT);
    }

    private void importAgendaDocument(Uri uri) {
        if (uri == null) return;
        try {
            getContentResolver().takePersistableUriPermission(uri, Intent.FLAG_GRANT_READ_URI_PERMISSION);
        } catch (Exception ignored) {}
        Toast.makeText(this, "Lettura della prenotazione in corso…", Toast.LENGTH_SHORT).show();
        dataExecutor.execute(() -> {
            try {
                String raw = extractAgendaText(uri);
                if (raw == null || raw.trim().isEmpty()) throw new Exception("no text");
                JSONObject parsed = parseAgendaText(raw);
                parsed.put("source_uri", uri.toString());
                String mime = getContentResolver().getType(uri);
                parsed.put("source_mime", mime == null ? "application/octet-stream" : mime);
                parsed.put("imported", true);
                final JSONObject ready = parsed;
                runOnUiThread(() -> showAgendaDialog(ready));
            } catch (Exception e) {
                runOnUiThread(() -> Toast.makeText(this, "Non sono riuscito a leggere automaticamente la prenotazione. Il file non è stato modificato.", Toast.LENGTH_LONG).show());
            }
        });
    }

    private String extractAgendaText(Uri uri) throws Exception {
        String mime = getContentResolver().getType(uri);
        boolean pdf = "application/pdf".equalsIgnoreCase(mime) || uri.toString().toLowerCase(Locale.ITALY).endsWith(".pdf");
        com.google.mlkit.vision.text.TextRecognizer recognizer = com.google.mlkit.vision.text.TextRecognition.getClient(com.google.mlkit.vision.text.latin.TextRecognizerOptions.DEFAULT_OPTIONS);
        try {
            StringBuilder out = new StringBuilder();
            if (!pdf) {
                com.google.mlkit.vision.common.InputImage image = com.google.mlkit.vision.common.InputImage.fromFilePath(this, uri);
                com.google.mlkit.vision.text.Text result = com.google.android.gms.tasks.Tasks.await(recognizer.process(image));
                return result.getText();
            }
            try (android.os.ParcelFileDescriptor pfd = getContentResolver().openFileDescriptor(uri, "r");
                 android.graphics.pdf.PdfRenderer renderer = new android.graphics.pdf.PdfRenderer(pfd)) {
                int pages = Math.min(renderer.getPageCount(), 4);
                for (int n = 0; n < pages; n++) {
                    android.graphics.pdf.PdfRenderer.Page page = renderer.openPage(n);
                    int w = Math.max(1, page.getWidth());
                    int h = Math.max(1, page.getHeight());
                    float scale = Math.min(2.2f, 2200f / Math.max(w, h));
                    scale = Math.max(1.0f, scale);
                    Bitmap bitmap = Bitmap.createBitmap(Math.max(1, Math.round(w * scale)), Math.max(1, Math.round(h * scale)), Bitmap.Config.ARGB_8888);
                    bitmap.eraseColor(Color.WHITE);
                    page.render(bitmap, null, null, android.graphics.pdf.PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY);
                    page.close();
                    com.google.mlkit.vision.common.InputImage image = com.google.mlkit.vision.common.InputImage.fromBitmap(bitmap, 0);
                    com.google.mlkit.vision.text.Text result = com.google.android.gms.tasks.Tasks.await(recognizer.process(image));
                    if (out.length() > 0) out.append('\n');
                    out.append(result.getText());
                    bitmap.recycle();
                }
            }
            return out.toString();
        } finally {
            recognizer.close();
        }
    }

    private JSONObject parseAgendaText(String raw) throws Exception {
        String normalized = raw.replace('\r', '\n');
        String[] rawLines = normalized.split("\\n+");
        java.util.ArrayList<String> lines = new java.util.ArrayList<>();
        for (String r : rawLines) {
            String line = r == null ? "" : r.trim().replaceAll("\\s+", " ");
            if (!line.isEmpty()) lines.add(line);
        }

        java.util.regex.Pattern datePattern = java.util.regex.Pattern.compile("\\b(\\d{2}/\\d{2}/\\d{4})\\b");
        java.util.regex.Pattern timePattern = java.util.regex.Pattern.compile("\\b([01]?\\d|2[0-3]):[0-5]\\d\\b");
        String title = "";
        String date = "";
        String time = "";
        String location = "";
        String appointmentLine = "";

        for (String line : lines) {
            String low = line.toLowerCase(Locale.ITALY);
            if (low.startsWith("servizio:")) {
                title = line.substring(line.indexOf(':') + 1).trim();
            }
            java.util.regex.Matcher dm = datePattern.matcher(line);
            java.util.regex.Matcher tm = timePattern.matcher(line);
            if (date.isEmpty() && dm.find() && tm.find()) {
                date = dm.group(1);
                time = tm.group();
                appointmentLine = line;
            }
        }

        if (title.isEmpty() && !appointmentLine.isEmpty()) {
            String candidate = appointmentLine;
            candidate = candidate.replaceAll("(?i)(Lun|Mar|Mer|Gio|Ven|Sab|Dom)[- ]?", " ");
            candidate = datePattern.matcher(candidate).replaceAll(" ");
            candidate = timePattern.matcher(candidate).replaceAll(" ");
            candidate = candidate.replaceAll("(?i)Non Disponibile.*$", " ");
            candidate = candidate.replaceAll("^[A-Z0-9]{2,8}\\s+", "");
            candidate = candidate.replaceAll("\\s+", " ").trim();
            if (candidate.length() >= 3) title = candidate;
        }

        if (title.isEmpty()) {
            for (int i = 0; i < lines.size(); i++) {
                String low = lines.get(i).toLowerCase(Locale.ITALY);
                if (low.equals("prestazione") || low.startsWith("prestazione ")) {
                    for (int j = i + 1; j < Math.min(lines.size(), i + 4); j++) {
                        String candidate = lines.get(j);
                        if (candidate.length() > 3 && !candidate.toLowerCase(Locale.ITALY).contains("data ora")) {
                            title = candidate.replaceAll("^[A-Z0-9]{2,8}\\s+", "").trim();
                            break;
                        }
                    }
                    if (!title.isEmpty()) break;
                }
            }
        }
        if (title.isEmpty()) title = "Appuntamento sanitario";

        for (int i = 0; i < lines.size() && location.isEmpty(); i++) {
            String line = lines.get(i);
            String low = line.toLowerCase(Locale.ITALY);
            if (low.contains("presentarsi al seguente indirizzo")) {
                int colon = line.indexOf(':');
                if (colon >= 0 && colon + 1 < line.length()) location = line.substring(colon + 1).trim();
                if (location.isEmpty()) {
                    for (int j = i + 1; j < Math.min(lines.size(), i + 5); j++) {
                        String c = lines.get(j);
                        String cl = c.toLowerCase(Locale.ITALY);
                        if (cl.contains(" via ") || cl.startsWith("via ") || cl.contains(" piazza ") || cl.contains(" viale ")) { location = c; break; }
                    }
                }
            }
        }
        for (int i = 0; i < lines.size() && location.isEmpty(); i++) {
            String low = lines.get(i).toLowerCase(Locale.ITALY);
            if (low.contains("dove presentarsi")) {
                for (int j = i + 1; j < Math.min(lines.size(), i + 7); j++) {
                    String c = lines.get(j);
                    String cl = c.toLowerCase(Locale.ITALY);
                    if (cl.contains(" via ") || cl.startsWith("via ") || cl.contains(" piazza ") || cl.contains(" viale ")) { location = c; break; }
                }
            }
        }
        for (String line : lines) {
            if (!location.isEmpty()) break;
            String low = line.toLowerCase(Locale.ITALY);
            if (low.startsWith("luogo:") || low.startsWith("indirizzo:")) location = line.substring(line.indexOf(':') + 1).trim();
        }

        java.util.LinkedHashSet<String> instructions = new java.util.LinkedHashSet<>();
        java.util.LinkedHashSet<String> routes = new java.util.LinkedHashSet<>();
        java.util.LinkedHashSet<String> refs = new java.util.LinkedHashSet<>();
        for (String line : lines) {
            String low = line.toLowerCase(Locale.ITALY);
            if (low.contains("padiglione") || low.contains("ambulatorio") || low.contains("piano ") || low.startsWith("piano ") || low.contains("ingresso") || low.contains("percorso") || low.contains("presentarsi al seguente indirizzo")) routes.add(line);
            if (low.contains("digiun") || low.contains("bere acqua") || low.contains("sospend") || low.contains("assum") || low.contains("portare") || low.contains("porti con") || low.contains("arriv") || (low.contains("presentarsi") && low.contains("minut")) || low.contains("vescica") || low.contains("preparaz") || low.contains("esami precedenti")) instructions.add(line);
            if (low.contains("nre") || low.contains("pincode") || low.contains("iuv") || low.startsWith("prenotazione") || low.contains("impegnativa")) {
                if (line.length() <= 180) refs.add(line);
            }
        }

        String titleLow = title.toLowerCase(Locale.ITALY);
        String type;
        if (titleLow.contains("telefon")) type = "Telefonare";
        else if (titleLow.contains("visita")) type = "Prenotazione visita";
        else type = "Prenotazione esami";

        StringBuilder notes = new StringBuilder();
        if (!routes.isEmpty()) {
            notes.append("Indicazioni per raggiungere l'ambulatorio / la sede:\n");
            for (String x : routes) notes.append("• ").append(x).append('\n');
        }
        if (!instructions.isEmpty()) {
            if (notes.length() > 0) notes.append('\n');
            notes.append("Indicazioni dalla prenotazione:\n");
            for (String x : instructions) notes.append("• ").append(x).append('\n');
        }
        if (!refs.isEmpty()) {
            if (notes.length() > 0) notes.append('\n');
            notes.append("Riferimenti:\n");
            for (String x : refs) notes.append("• ").append(x).append('\n');
        }
        if (notes.length() > 0) notes.append('\n');
        notes.append("Per tutte le informazioni necessarie, consulta il file originale allegato.");

        JSONObject out = new JSONObject();
        out.put("type", type);
        out.put("title", title);
        out.put("date", date);
        out.put("time", time);
        out.put("location", location);
        out.put("notes", notes.toString().trim());
        return out;
    }

    private void openAgendaOriginal(JSONObject item) {
        try {
            Uri uri = Uri.parse(item.optString("source_uri", ""));
            if (uri == null) return;
            Intent i = new Intent(Intent.ACTION_VIEW);
            i.setDataAndType(uri, item.optString("source_mime", "application/octet-stream"));
            i.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
            startActivity(i);
        } catch (Exception e) {
            Toast.makeText(this, "Il file originale non è più disponibile in questa posizione", Toast.LENGTH_LONG).show();
        }
    }

    private String normalizeAgendaText(String value) {
        if (value == null) return "";
        String n = java.text.Normalizer.normalize(value, java.text.Normalizer.Form.NFD).replaceAll("\\p{M}+", "").toLowerCase(Locale.ITALY);
        return n.replaceAll("[^a-z0-9]+", " ").trim().replaceAll("\\s+", " ");
    }

    private JSONObject findSimilarAgendaItem(JSONObject candidate) {
        JSONArray array = readArray(PREF_AGENDA);
        long id = candidate.optLong("id", 0L);
        String date = candidate.optString("date", "").trim();
        String time = candidate.optString("time", "").trim();
        String title = normalizeAgendaText(candidate.optString("title", ""));
        String location = normalizeAgendaText(candidate.optString("location", ""));
        for (int i = 0; i < array.length(); i++) {
            JSONObject other = array.optJSONObject(i);
            if (other == null || other.optLong("id", -1L) == id) continue;
            if (!date.equals(other.optString("date", "").trim())) continue;
            String ot = other.optString("time", "").trim();
            if (!time.isEmpty() && !ot.isEmpty() && !time.equals(ot)) continue;
            String otherTitle = normalizeAgendaText(other.optString("title", ""));
            boolean titleMatch = !title.isEmpty() && !otherTitle.isEmpty() && (title.equals(otherTitle) || title.contains(otherTitle) || otherTitle.contains(title));
            String otherLocation = normalizeAgendaText(other.optString("location", ""));
            boolean locationMatch = !location.isEmpty() && !otherLocation.isEmpty() && (location.equals(otherLocation) || location.contains(otherLocation) || otherLocation.contains(location));
            if (titleMatch || (locationMatch && !time.isEmpty() && time.equals(ot))) return other;
        }
        return null;
    }

    private void showDuplicateAgendaDialog(JSONObject imported, JSONObject previous) {
        String message = "Sono presenti 2 appuntamenti simili. Prima di qualsiasi sincronizzazione esterna scegli quale mantenere.\n\n" +
                "PRECEDENTE\n" + previous.optString("title", "Appuntamento") + "\n" + previous.optString("date", "") + " " + previous.optString("time", "") + "\n" + previous.optString("location", "") +
                "\n\nNUOVO / IMPORTATO\n" + imported.optString("title", "Appuntamento") + "\n" + imported.optString("date", "") + " " + imported.optString("time", "") + "\n" + imported.optString("location", "");
        new AlertDialog.Builder(this)
                .setTitle("Possibile appuntamento duplicato")
                .setMessage(message)
                .setNegativeButton("Mantieni precedente", (d, w) -> resolveAgendaDuplicate(previous, imported))
                .setPositiveButton("Mantieni importato", (d, w) -> resolveAgendaDuplicate(imported, previous))
                .setNeutralButton("Mantieni entrambi", (d, w) -> clearDuplicateHold(imported))
                .show();
    }

    private void clearDuplicateHold(JSONObject item) {
        try {
            item.remove("duplicate_hold");
            upsertRecord(PREF_AGENDA, item);
            refreshAgendaCard(item);
            mirrorAgendaToClinicalAsync(item);
        } catch (Exception ignored) {}
    }

    private void resolveAgendaDuplicate(JSONObject keep, JSONObject drop) {
        try {
            JSONObject merged = new JSONObject(keep.toString());
            if (merged.optString("source_uri", "").isEmpty() && !drop.optString("source_uri", "").isEmpty()) {
                merged.put("source_uri", drop.optString("source_uri", ""));
                merged.put("source_mime", drop.optString("source_mime", "application/octet-stream"));
                merged.put("imported", true);
            }
            if (merged.optString("location", "").isEmpty() && !drop.optString("location", "").isEmpty()) merged.put("location", drop.optString("location", ""));
            String keepNotes = merged.optString("notes", "").trim();
            String dropNotes = drop.optString("notes", "").trim();
            if (!dropNotes.isEmpty() && !keepNotes.contains(dropNotes)) merged.put("notes", keepNotes.isEmpty() ? dropNotes : keepNotes + "\n\n" + dropNotes);
            copySyncLinkFields(drop, merged);
            merged.remove("duplicate_hold");
            upsertRecord(PREF_AGENDA, merged);
            refreshAgendaCard(merged);
            mirrorAgendaToClinicalAsync(merged);
            deleteAgendaLocal(drop.optLong("id", -1L));
            Toast.makeText(this, "Duplicato risolto: resta un solo appuntamento", Toast.LENGTH_SHORT).show();
        } catch (Exception e) {
            Toast.makeText(this, "Risoluzione duplicato non riuscita", Toast.LENGTH_LONG).show();
        }
    }

    private void deleteAgendaLocal(long id) {
        if (id < 0) return;
        JSONArray agenda = readArray(PREF_AGENDA);
        for (int i = agenda.length() - 1; i >= 0; i--) {
            JSONObject obj = agenda.optJSONObject(i);
            if (obj != null && obj.optLong("id", -1L) == id) agenda.remove(i);
        }
        saveArray(PREF_AGENDA, agenda);
        removeAgendaCard(id);
        removeAgendaClinicalMirrorAsync(id);
    }

'''
    s = s[:dialog_start] + dialog + s[dialog_end:]

    pref_marker = '    private void renderBackup() {'
    if pref_marker not in s:
        raise SystemExit('R11 patch failed: preferences insertion point missing')
    preferences = r'''    private void renderPreferenze() {
        LinearLayout c = card();
        c.addView(sectionHeader("Avvisi predefiniti Agenda"));
        c.addView(text("Questi avvisi vengono proposti automaticamente per tutte le sezioni dell'Agenda. L'impostazione iniziale è 1 giorno prima; puoi scegliere fino a 5 avvisi.", 13, MUTED, false));
        final int[] values = agendaAlertValues();
        final String[] labels = agendaAlertLabels();
        final android.widget.CheckBox[] checks = new android.widget.CheckBox[values.length];
        String current = prefs.getString(PREF_AGENDA_ALERTS, "1440");
        for (int i = 0; i < values.length; i++) {
            android.widget.CheckBox cb = new android.widget.CheckBox(this);
            cb.setText(labels[i]);
            cb.setTextColor(TEXT);
            cb.setChecked(csvHasInt(current, values[i]));
            cb.setOnCheckedChangeListener((button, checked) -> {
                if (checked && countChecked(checks) > 5) {
                    button.setChecked(false);
                    Toast.makeText(this, "Puoi impostare al massimo 5 avvisi", Toast.LENGTH_SHORT).show();
                }
            });
            checks[i] = cb;
            c.addView(cb);
        }
        Button save = button("Salva avvisi predefiniti");
        save.setOnClickListener(v -> {
            prefs.edit().putString(PREF_AGENDA_ALERTS, checkedAlertsCsv(checks, values)).apply();
            Toast.makeText(this, "Preferenze Agenda salvate", Toast.LENGTH_SHORT).show();
        });
        c.addView(save, matchWrapTop(10));
        content.addView(c, matchWrapBottom(14));

        LinearLayout meds = card();
        meds.addView(sectionHeader("Raggruppamento riordini farmaci"));
        meds.addView(text("Il raggruppamento delle scadenze di riordino è una regola separata e vale esclusivamente per la sezione farmaci. Non modifica gli altri appuntamenti dell'Agenda.", 13, MUTED, false));
        content.addView(meds, matchWrapBottom(14));
    }

'''
    s = s.replace(pref_marker, preferences + pref_marker, 1)

    result_marker = '        if (requestCode == CREATE_BACKUP) {'
    if result_marker not in s:
        raise SystemExit('R11 patch failed: activity result insertion point missing')
    result_block = r'''        if (requestCode == IMPORT_AGENDA_DOCUMENT) {
            if (resultCode == RESULT_OK && data != null && data.getData() != null) importAgendaDocument(data.getData());
            return;
        }

'''
    s = s.replace(result_marker, result_block + result_marker, 1)

    visible = {
        'Android R10 TEST': 'Android R11 TEST',
        'Aiuto R10': 'Aiuto R11',
        'R10: struttura presente': 'R11: struttura presente',
        'R10 mantiene lo stesso pacchetto Android': 'R11 mantiene lo stesso pacchetto Android',
        'Installala sopra la R9': 'Installala sopra la R10',
        'Importazione file non ancora attiva nella R10': 'Importa PDF, foto o scansioni direttamente nell’Agenda quando contengono una prenotazione.'
    }
    for old, new in visible.items():
        s = s.replace(old, new)

    MAIN.write_text(s, encoding='utf-8')


def patch_editor():
    s = EDITOR.read_text(encoding='utf-8')
    # Auto bordi è approvato: non viene toccato.
    s = s.replace('Imgproc.createCLAHE(3.2, new Size(8, 8))', 'Imgproc.createCLAHE(2.4, new Size(8, 8))')
    s = s.replace('Core.addWeighted(enhancedRgb, 1.62, blur, -0.62, 0, sharp);', 'Core.addWeighted(enhancedRgb, 1.35, blur, -0.35, 0, sharp);')
    s = s.replace('sharp.convertTo(sharp, -1, 1.04, 2);', 'sharp.convertTo(sharp, -1, 1.01, 1);')
    s = s.replace('Leggibilità migliorata con intervento moderato.', 'Leggibilità migliorata con intervento leggero e conservativo.')
    s = s.replace('Imgproc.createCLAHE(1.8, new Size(8, 8))', 'Imgproc.createCLAHE(1.4, new Size(8, 8))')
    s = s.replace('Core.addWeighted(contrast, 1.28, blur, -0.28, 0, sharp);', 'Core.addWeighted(contrast, 1.15, blur, -0.15, 0, sharp);')
    s = s.replace('Bianco e nero leggibile applicato senza soglia aggressiva.', 'Bianco e nero naturale applicato preservando i dettagli del documento.')
    EDITOR.write_text(s, encoding='utf-8')


patch_main()
patch_editor()
print('Android R11 agenda/import/preferences patch applied successfully')
