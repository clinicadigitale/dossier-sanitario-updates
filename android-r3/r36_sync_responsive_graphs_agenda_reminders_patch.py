from pathlib import Path

BASE = Path('android-r3/app/src/main/java/it/dossiersanitario/clinicadigitale/beta')
MAIN = BASE / 'R6MainActivity.java'
CLOUD = BASE / 'R12CloudManager.java'
GRADLE = Path('android-r3/app/build.gradle')


def require(text, needle, label):
    if needle not in text:
        raise SystemExit(f'R36 patch failed: missing {label}')


def replace_block(text, signature, replacement, label=None):
    start = text.find(signature)
    if start < 0:
        raise SystemExit(f'R36 patch failed: missing {label or signature}')
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
        raise SystemExit(f'R36 patch failed: unclosed {label or signature}')
    return text[:start] + replacement.rstrip() + '\n' + text[end:]


# ---------------------------------------------------------------------------
# 1. Cloud sync: R35 could finish without errors while the exact Windows view
#    remained on an old snapshot. Reconcile the newest committed snapshot first
#    (bounded streaming, no whole-snapshot byte array), then apply change batches.
#    Never overwrite pending local Android edits with a full snapshot refresh.
# ---------------------------------------------------------------------------
c = CLOUD.read_text(encoding='utf-8')

sync_now = r'''    public static String syncNow(Context context, SharedPreferences prefs, boolean background) throws Exception {
        synchronized (R12CloudManager.class) { if (syncing) return "Sincronizzazione già in corso"; syncing = true; }
        try {
            JSONObject cfg = loadConfig(prefs);
            if (cfg.optString("archiveId", "").isEmpty()) return "Dossier cloud non configurato";
            if (archiveRoot(context, cfg, false) == null) throw new Exception("Archivio Dossier non disponibile. Reinserisci la memoria selezionata.");
            if (prefs.getString(PENDING_COMPLETION_KEY, "").length() > 2) {
                try { publishPendingCompletion(context, prefs, cfg); } catch (Exception ignored) {}
            }

            boolean snapshotSafe = readArray(prefs, QUEUE_KEY).length() == 0;
            int snapshotUpdated = snapshotSafe ? r36RefreshLatestCommittedSnapshot(context, prefs, cfg) : 0;
            int received = pullRemoteChanges(context, prefs, cfg, false);
            int sent = uploadPendingChanges(context, prefs, cfg);
            checkCompletionConsumed(context, prefs, cfg);
            cfg.put("lastSyncAt", Instant.now().toString());
            saveConfig(prefs, cfg);
            String suffix = snapshotUpdated > 0 ? " · archivio Windows aggiornato" : "";
            return sent + " inviate · " + received + " ricevute" + suffix;
        } finally {
            synchronized (R12CloudManager.class) { syncing = false; }
        }
    }'''
c = replace_block(c, '    public static String syncNow(Context context, SharedPreferences prefs, boolean background) throws Exception {', sync_now, 'syncNow')

pull_marker = '    private static int pullRemoteChanges(Context context, SharedPreferences prefs, JSONObject cfg, boolean initial) throws Exception {'
require(c, pull_marker, 'pullRemoteChanges insertion point')
snapshot_helper = r'''    private static int r36RefreshLatestCommittedSnapshot(Context context, SharedPreferences prefs, JSONObject cfg) throws Exception {
        SnapshotInfo latest = latestSnapshot(context, cfg);
        if (latest == null || latest.name == null || latest.name.trim().isEmpty()) return 0;

        String reconciled = cfg.optString("r36ReconciledSnapshotName", "");
        String configured = cfg.optString("lastSnapshotName", "");
        boolean firstR36Reconciliation = reconciled.isEmpty();
        if (!firstR36Reconciliation && latest.name.equals(reconciled)) return 0;

        File root = archiveRoot(context, cfg, false);
        if (root == null) throw new Exception("Archivio Dossier non disponibile.");
        long required = requiredBytes(Math.max(0L, latest.size));
        if (latest.size > 0 && freeBytes(root) < required) {
            throw new Exception("Spazio insufficiente per aggiornare il Dossier: servono " + formatBytes(required) + ".");
        }

        File encryptedPart = new File(root, "r36_snapshot_refresh.dsl5.part");
        File plainZip = new File(context.getCacheDir(), "r36_snapshot_refresh.zip");
        if (encryptedPart.exists()) encryptedPart.delete();
        if (plainZip.exists()) plainZip.delete();
        try {
            R12Rclone.copyFromRemote(context, cloudRoot(cfg) + "/snapshots/" + latest.name, encryptedPart);
            if (latest.size > 0 && encryptedPart.length() != latest.size) {
                throw new Exception("La copia cloud più recente non ha la dimensione attesa.");
            }

            byte[] recovery = recoveryKey(context, cfg);
            try (InputStream decrypted = R12Crypto.openDsl5File(encryptedPart, recovery);
                 FileOutputStream out = new FileOutputStream(plainZip)) {
                byte[] buffer = new byte[256 * 1024];
                int n;
                while ((n = decrypted.read(buffer)) >= 0) if (n > 0) out.write(buffer, 0, n);
                out.flush();
            }
            if (!plainZip.isFile() || plainZip.length() == 0) throw new Exception("Snapshot Windows decifrato non disponibile.");

            R30BoundedWindows.importSnapshot(context, prefs, cfg, plainZip, null);
            File finalFile = new File(root, "current_snapshot.dsl5");
            replaceVerified(encryptedPart, finalFile);
            cfg.put("lastSnapshotName", latest.name);
            cfg.put("r36ReconciledSnapshotName", latest.name);
            cfg.put("r36SnapshotReconciledAt", Instant.now().toString());
            saveConfig(prefs, cfg);
            return 1;
        } finally {
            if (plainZip.exists()) plainZip.delete();
            if (encryptedPart.exists()) encryptedPart.delete();
        }
    }

'''
c = c.replace(pull_marker, snapshot_helper + pull_marker, 1)
CLOUD.write_text(c, encoding='utf-8')


# ---------------------------------------------------------------------------
# 2. Responsive rotation, report-backed graphs, agenda source documents and
#    human-readable reminder intervals.
# ---------------------------------------------------------------------------
s = MAIN.read_text(encoding='utf-8')

# Use more of the available width when the phone is rotated.
old_padding = '        content.setPadding(dp(16), dp(4), dp(16), dp(28));'
require(s, old_padding, 'content padding')
s = s.replace(old_padding,
'''        int r36ContentSide = r36Landscape() ? dp(24) : dp(16);
        content.setPadding(r36ContentSide, dp(4), r36ContentSide, dp(28));''', 1)

label_value = r'''    private LinearLayout labelValue(String label, String value) {
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setGravity(Gravity.TOP);
        row.setPadding(0, dp(5), 0, dp(5));

        boolean landscape = r36Landscape();
        int screenWidth = getResources().getDisplayMetrics().widthPixels;
        int labelWidth = landscape
                ? Math.max(dp(160), Math.min(dp(270), Math.round(screenWidth * 0.34f)))
                : dp(100);
        TextView labelView = text(label, 13, MUTED, false);
        labelView.setMaxLines(landscape ? 2 : 4);
        row.addView(labelView, new LinearLayout.LayoutParams(labelWidth, ViewGroup.LayoutParams.WRAP_CONTENT));

        String visibleValue = r36HumanReminderDisplay(label, value);
        TextView valueView = text(visibleValue, 13, TEXT, true);
        r34MakeContactAction(valueView, label, value);
        row.addView(valueView, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        return row;
    }'''
s = replace_block(s, '    private LinearLayout labelValue(String label, String value) {', label_value, 'responsive labelValue')

# Clinical selector: every option is anchored to the date of its own series and
# the list is sorted chronologically. Laboratory series come from report data.
selector = r'''    private void r31SelectClinicalValue(boolean graph) {
        java.util.ArrayList<JSONObject> choices = new java.util.ArrayList<>();

        JSONArray labs = R36ClinicalSeries.availableLabParameters(prefs);
        for (int i = 0; i < labs.length(); i++) {
            JSONObject p = labs.optJSONObject(i);
            if (p == null) continue;
            String id = p.optString("id", "");
            if (id.isEmpty()) continue;
            String label = p.optString("name", id);
            String unit = p.optString("unit", "");
            if (!unit.isEmpty()) label += " (" + unit + ")";
            label += " · referti";
            r36AddClinicalChoice(choices, label, "l|" + id + "|value|" + label, R36ClinicalSeries.labSeries(prefs, id));
        }

        r36AddClinicalChoice(choices, "Peso", "u|weight|value|Peso", R27ExactWindows.measurementsOf(prefs, "weight"));
        r36AddClinicalChoice(choices, "Saturazione ossigeno", "u|spo2|value|Saturazione ossigeno", R27ExactWindows.measurementsOf(prefs, "spo2"));
        r36AddClinicalChoice(choices, "Glicemia manuale", "u|glucose|value|Glicemia manuale", R27ExactWindows.measurementsOf(prefs, "glucose"));
        r36AddClinicalChoice(choices, "Frequenza cardiaca", "u|heart_rate|value|Frequenza cardiaca", R27ExactWindows.measurementsOf(prefs, "heart_rate"));
        JSONArray pressure = R27ExactWindows.measurementsOf(prefs, "blood_pressure");
        if (graph) {
            r36AddClinicalChoice(choices, "Pressione arteriosa", "p|blood_pressure|both|Pressione arteriosa", pressure);
            r36AddClinicalChoice(choices, "Frequenza da pressione", "u|blood_pressure|heartRate|Frequenza da pressione", pressure);
        } else {
            r36AddClinicalChoice(choices, "Pressione sistolica", "u|blood_pressure|systolic|Pressione sistolica", pressure);
            r36AddClinicalChoice(choices, "Pressione diastolica", "u|blood_pressure|diastolic|Pressione diastolica", pressure);
            r36AddClinicalChoice(choices, "Frequenza da pressione", "u|blood_pressure|heartRate|Frequenza da pressione", pressure);
        }

        if (choices.isEmpty()) {
            Toast.makeText(this, "Nessun parametro disponibile", Toast.LENGTH_SHORT).show();
            return;
        }
        choices.sort((a, b) -> {
            int byDate = a.optString("sortDate", "9999-99-99").compareTo(b.optString("sortDate", "9999-99-99"));
            return byDate != 0 ? byDate : a.optString("label", "").compareToIgnoreCase(b.optString("label", ""));
        });
        String[] labels = new String[choices.size()];
        String[] codes = new String[choices.size()];
        for (int i = 0; i < choices.size(); i++) {
            labels[i] = choices.get(i).optString("label", "Parametro");
            codes[i] = choices.get(i).optString("code", "");
        }
        new AlertDialog.Builder(this)
                .setTitle(graph ? "Seleziona valore da visualizzare" : "Seleziona valore da confrontare")
                .setItems(labels, (d, which) -> {
                    prefs.edit().putString(graph ? "r31_graph_choice" : "r31_compare_choice", codes[which]).apply();
                    renderSection(graph ? "Grafici" : "Confronta");
                })
                .setNegativeButton("Annulla", null)
                .show();
    }'''
s = replace_block(s, '    private void r31SelectClinicalValue(boolean graph) {', selector, 'clinical selector')

series_method = r'''    private JSONArray r31SeriesForChoice(String choice) {
        String[] p = choice == null ? new String[0] : choice.split("\\|", 4);
        if (p.length < 4) return new JSONArray();
        if ("l".equals(p[0])) return R36ClinicalSeries.labSeries(prefs, p[1]);
        if ("u".equals(p[0])) return R27ExactWindows.measurementsOf(prefs, p[1]);
        if ("m".equals(p[0])) {
            // Compatibility with choices saved by R31-R35. Old "Glicemia domestica"
            // now resolves to the report-backed glycaemia series when it exists.
            if ("glucose".equalsIgnoreCase(p[1])) {
                String reportId = R36ClinicalSeries.findParameterByName(prefs, "glicem");
                if (!reportId.isEmpty()) {
                    JSONArray reports = R36ClinicalSeries.labSeries(prefs, reportId);
                    if (reports.length() > 0) return reports;
                }
            }
            return R27ExactWindows.measurementsOf(prefs, p[1]);
        }
        return new JSONArray();
    }'''
s = replace_block(s, '    private JSONArray r31SeriesForChoice(String choice){', series_method, 'series for choice')

choice_label = r'''    private String r31ChoiceLabel(String choice) {
        String[] p = choice == null ? new String[0] : choice.split("\\|", 4);
        if (p.length < 4) return "Parametro";
        if ("m".equals(p[0]) && "glucose".equalsIgnoreCase(p[1])) {
            String reportId = R36ClinicalSeries.findParameterByName(prefs, "glicem");
            if (!reportId.isEmpty()) return "Glicemia · referti";
        }
        return p[3];
    }'''
s = replace_block(s, '    private String r31ChoiceLabel(String choice){', choice_label, 'choice label')

# Agenda: original document only for a document-derived visit/exam booking.
agenda = r'''    private void renderAgenda() {
        JSONArray rows = R27ExactWindows.calendarEvents(prefs);
        boolean nearestFirst = prefs.getBoolean("r32_agenda_nearest_first", true);
        LinearLayout intro = card();
        intro.addView(sectionHeader("Agenda"));
        intro.addView(labelValue("Eventi registrati", String.valueOf(rows.length())));
        Button add = button("Nuovo appuntamento");
        add.setOnClickListener(v -> r31EditAgendaEvent(null));
        intro.addView(add, matchWrapTop(8));
        Button sync = button("Sincronizza Agenda");
        sync.setOnClickListener(v -> R12CloudManager.syncInteractiveR31(this, prefs));
        intro.addView(sync, matchWrapTop(8));
        Button order = button(nearestFirst ? "Ordine: appuntamenti più vicini prima" : "Ordine: appuntamenti più lontani prima");
        order.setOnClickListener(v -> {
            prefs.edit().putBoolean("r32_agenda_nearest_first", !nearestFirst).apply();
            renderSection("Agenda");
        });
        intro.addView(order, matchWrapTop(8));
        content.addView(intro, matchWrapBottom(14));

        java.util.ArrayList<JSONObject> ordered = r31SortedByDate(rows, nearestFirst, "startDate", "date", "createdAt");
        if (!nearestFirst) java.util.Collections.reverse(ordered);
        if (ordered.isEmpty()) {
            LinearLayout e = card();
            e.addView(text("Nessun evento registrato.", 13, MUTED, false));
            content.addView(e, matchWrapBottom(14));
            return;
        }
        for (JSONObject row : ordered) {
            LinearLayout c = card();
            c.addView(text(r31First(row, "title", "name", "category"), 16, TEXT, true));
            r31AddIf(c, "Tipo", r31CategoryItalian(r31First(row, "category", "type")));
            r31AddIf(c, "Data", r31First(row, "startDate", "date"));
            String time = r31First(row, "startTime", "time");
            c.addView(labelValue("Ora", row.optBoolean("allDay", false) || time.isEmpty() ? "Tutto il giorno" : time));
            if (row.has("durationMinutes")) c.addView(labelValue("Durata", row.optInt("durationMinutes", 60) + " minuti"));
            r31AddIf(c, "Stato", r31StatusItalian(row.optString("status", "")));
            r31AddIf(c, "Luogo / struttura", row.optString("location", ""));
            JSONArray reminders = row.optJSONArray("reminders");
            if (reminders != null && reminders.length() > 0) c.addView(labelValue("Avvisi", r31JoinArray(reminders)));
            r31AddIf(c, "Note", row.optString("notes", ""));

            JSONObject sourceDoc = r36AgendaSourceDocument(row);
            if (sourceDoc != null) {
                Button original = button("Apri documento originale");
                original.setOnClickListener(v -> R27ExactWindows.openDocument(this, sourceDoc));
                c.addView(original, matchWrapTop(8));
            }
            Button edit = button("Modifica appuntamento");
            edit.setOnClickListener(v -> r31EditAgendaEvent(row));
            c.addView(edit, matchWrapTop(8));
            content.addView(c, matchWrapBottom(10));
        }
    }'''
s = replace_block(s, '    private void renderAgenda() {', agenda, 'Agenda')

agenda_edit = r'''    private void r31EditAgendaEvent(JSONObject source) {
        JSONObject base = source == null ? new JSONObject() : source;
        LinearLayout form = new LinearLayout(this);
        form.setOrientation(LinearLayout.VERTICAL);
        form.setPadding(dp(16), dp(8), dp(16), dp(8));
        EditText category = field("Tipo", r31CategoryItalian(base.optString("category", "Visita")));
        EditText title = field("Titolo", base.optString("title", ""));
        EditText date = field("Data (AAAA-MM-GG)", base.optString("startDate", ""));
        EditText time = field("Ora (HH:MM)", base.optString("startTime", ""));
        EditText duration = field("Durata in minuti", String.valueOf(base.optInt("durationMinutes", 60)));
        EditText status = field("Stato", r31StatusItalian(base.optString("status", "programmato")));
        EditText location = field("Luogo / struttura", base.optString("location", ""));
        EditText notes = field("Note", base.optString("notes", ""));
        JSONArray rem = base.optJSONArray("reminders");
        EditText reminders = field("Avvisi (es. 1 giorno; 2 ore; 30 minuti)", r36FormatReminderArray(rem == null ? r36SingleReminder(1440) : rem));
        CheckBox allDay = r31Check("Tutto il giorno", base.optBoolean("allDay", false));
        for (EditText e : new EditText[]{category, title, date, time, duration, status, location, notes, reminders}) form.addView(e);
        form.addView(allDay);
        ScrollView scroll = new ScrollView(this);
        scroll.addView(form);
        new AlertDialog.Builder(this)
                .setTitle(source == null ? "Nuovo appuntamento" : "Modifica appuntamento")
                .setView(scroll)
                .setNegativeButton("Annulla", null)
                .setPositiveButton("Salva", (d, w) -> {
                    try {
                        JSONObject updated = new JSONObject(base.toString());
                        if (updated.optString("id", "").isEmpty()) updated.put("id", "calevent_android_" + System.currentTimeMillis());
                        updated.put("profileId", R27ExactWindows.activeProfileId(prefs));
                        updated.put("category", clean(category));
                        updated.put("title", clean(title));
                        updated.put("startDate", clean(date));
                        updated.put("startTime", clean(time));
                        updated.put("durationMinutes", r31Int(clean(duration), 60));
                        updated.put("allDay", allDay.isChecked());
                        updated.put("status", r31AgendaStatusCode(clean(status)));
                        updated.put("location", clean(location));
                        updated.put("notes", clean(notes));
                        updated.put("reminders", r36ParseReminderText(clean(reminders)));
                        if (!R27ExactWindows.upsertData(prefs, "calendarEvents", updated)) throw new Exception("dati non salvati");
                        R12CloudManager.queueR31EntityPut(this, prefs, "calendarEvents", updated);
                        renderSection("Agenda");
                    } catch (Exception failure) {
                        Toast.makeText(this, "Salvataggio appuntamento non riuscito", Toast.LENGTH_LONG).show();
                    }
                }).show();
    }'''
s = replace_block(s, '    private void r31EditAgendaEvent(JSONObject source){', agenda_edit, 'Agenda edit reminders')

prefs_edit = r'''    private void r31EditGlobalPreferences(JSONObject source) {
        JSONObject base = source == null ? new JSONObject() : source;
        LinearLayout form = new LinearLayout(this);
        form.setOrientation(LinearLayout.VERTICAL);
        form.setPadding(dp(16), dp(8), dp(16), dp(8));
        EditText palette = field("Colore programma: teal, green, blue, burgundy, violet, graphite", base.optString("palette", "teal"));
        EditText theme = field("Aspetto: light o dark", base.optString("theme", "light"));
        EditText textScale = field("Dimensione testo: small, normal o large", base.optString("textScale", "normal"));
        EditText density = field("Spaziatura: comfortable o compact", base.optString("density", "comfortable"));
        EditText backup = field("Frequenza backup: daily, weekly, monthly o manual", base.optString("backupFrequency", "weekly"));
        EditText google = field("E-mail Google Calendar", base.optString("googleCalendarEmail", ""));
        EditText reorder = field("Giorni raggruppamento riordino (massimo 10)", String.valueOf(base.optInt("medicationReorderGroupDays", 7)));
        JSONArray rem = base.optJSONArray("agendaDefaultReminders");
        EditText reminders = field("Avvisi Agenda (es. 1 giorno; 2 ore; 30 minuti)", r36FormatReminderArray(rem == null ? r36SingleReminder(1440) : rem));
        CheckBox confirm = r31Check("Chiedi conferma prima delle importazioni", base.optBoolean("confirmImports", true));
        for (EditText e : new EditText[]{palette, theme, textScale, density, backup, google, reorder, reminders}) form.addView(e);
        form.addView(confirm);
        ScrollView scroll = new ScrollView(this);
        scroll.addView(form);
        new AlertDialog.Builder(this)
                .setTitle("Modifica preferenze generali")
                .setView(scroll)
                .setNegativeButton("Annulla", null)
                .setPositiveButton("Salva", (d, w) -> {
                    try {
                        JSONObject updated = new JSONObject(base.toString());
                        updated.put("palette", r31Allowed(clean(palette), new String[]{"teal", "green", "blue", "burgundy", "violet", "graphite"}, "teal"));
                        updated.put("theme", r31Allowed(clean(theme), new String[]{"light", "dark"}, "light"));
                        updated.put("textScale", r31Allowed(clean(textScale), new String[]{"small", "normal", "large"}, "normal"));
                        updated.put("density", r31Allowed(clean(density), new String[]{"comfortable", "compact"}, "comfortable"));
                        updated.put("backupFrequency", r31Allowed(clean(backup), new String[]{"daily", "weekly", "monthly", "manual"}, "weekly"));
                        updated.put("googleCalendarEmail", clean(google));
                        updated.put("medicationReorderGroupDays", Math.max(0, Math.min(10, r31Int(clean(reorder), 7))));
                        updated.put("agendaDefaultReminders", r36ParseReminderText(clean(reminders)));
                        updated.put("confirmImports", confirm.isChecked());
                        R27ExactWindows.updateGlobalPreferences(prefs, updated);
                        JSONObject entity = new JSONObject();
                        entity.put("id", "globalPreferences");
                        entity.put("key", "globalPreferences");
                        entity.put("value", updated);
                        R12CloudManager.queueR31EntityPut(this, prefs, "settings", entity);
                        loadR26ImportedUiSettings();
                        showMainUi(null);
                        renderSection("Preferenze");
                    } catch (Exception failure) {
                        Toast.makeText(this, "Salvataggio preferenze non riuscito", Toast.LENGTH_LONG).show();
                    }
                }).show();
    }'''
s = replace_block(s, '    private void r31EditGlobalPreferences(JSONObject source){', prefs_edit, 'global preferences reminders')

# Shared R36 helpers. The human-readable formatter is also used by labelValue,
# so any other existing section that displays raw reminder-minute lists benefits.
helper_marker = '    private void renderBackup() {'
require(s, helper_marker, 'R36 helper insertion point')
helpers = r'''    private boolean r36Landscape() {
        return getResources().getConfiguration().orientation == Configuration.ORIENTATION_LANDSCAPE;
    }

    private void r36AddClinicalChoice(java.util.ArrayList<JSONObject> choices, String label, String code, JSONArray series) {
        if (choices == null || label == null || code == null) return;
        if (series == null || series.length() == 0) return;
        try {
            JSONObject item = new JSONObject();
            item.put("label", label);
            item.put("code", code);
            item.put("sortDate", R36ClinicalSeries.chronologicalKey(series));
            choices.add(item);
        } catch (Exception ignored) {}
    }

    private JSONObject r36AgendaSourceDocument(JSONObject event) {
        if (event == null || !r36AgendaDocumentEligible(event)) return null;
        String id = event.optString("sourceDocumentId", "").trim();
        if (id.isEmpty()) id = event.optString("documentId", "").trim();
        if (id.isEmpty()) id = event.optString("sourceDocId", "").trim();
        if (id.isEmpty()) {
            JSONObject source = event.optJSONObject("sourceDocument");
            if (source != null) id = source.optString("id", source.optString("documentId", "")).trim();
        }
        if (id.isEmpty()) return null;
        return R27ExactWindows.documentById(prefs, id);
    }

    private boolean r36AgendaDocumentEligible(JSONObject event) {
        String raw = (r31First(event, "category", "type") + " " + r31First(event, "title", "name") + " " + event.optString("sourceType", "")).toLowerCase(java.util.Locale.ROOT);
        if (raw.contains("farmac") || raw.contains("terapi") || raw.contains("riord") || raw.contains("telefon") || raw.contains("chiamat")) return false;
        return raw.contains("visita") || raw.contains("visit") || raw.contains("esame") || raw.contains("exam") || raw.contains("prenotaz") || raw.contains("booking");
    }

    private JSONArray r36SingleReminder(int minutes) {
        JSONArray out = new JSONArray();
        out.put(minutes);
        return out;
    }

    private String r36HumanReminderDisplay(String label, String value) {
        if (label == null || value == null) return value == null ? "" : value;
        String l = label.toLowerCase(java.util.Locale.ROOT);
        if (!(l.contains("avvis") || l.contains("promem") || l.contains("preavvis") || l.contains("reminder"))) return value;
        String raw = value.trim();
        if (!raw.matches("[0-9\\s,;]+")) return value;
        JSONArray parsed = new JSONArray();
        for (String part : raw.split("[,;]")) {
            try { parsed.put(Integer.parseInt(part.trim())); } catch (Exception ignored) {}
        }
        return parsed.length() == 0 ? value : r36FormatReminderArray(parsed);
    }

    private String r36FormatReminderArray(JSONArray reminders) {
        if (reminders == null || reminders.length() == 0) return "Nessun avviso";
        StringBuilder out = new StringBuilder();
        for (int i = 0; i < reminders.length(); i++) {
            int minutes = reminders.optInt(i, -1);
            if (minutes < 0) continue;
            if (out.length() > 0) out.append("; ");
            out.append(r36FormatMinutes(minutes));
        }
        return out.length() == 0 ? "Nessun avviso" : out.toString();
    }

    private String r36FormatMinutes(int minutes) {
        if (minutes <= 0) return "0 minuti";
        if (minutes % 10080 == 0) {
            int n = minutes / 10080;
            return n == 1 ? "1 settimana" : n + " settimane";
        }
        if (minutes % 1440 == 0) {
            int n = minutes / 1440;
            return n == 1 ? "1 giorno" : n + " giorni";
        }
        if (minutes % 60 == 0) {
            int n = minutes / 60;
            return n == 1 ? "1 ora" : n + " ore";
        }
        if (minutes >= 60 && minutes % 30 == 0) {
            double hours = minutes / 60.0;
            String h = String.format(java.util.Locale.ITALY, "%.1f", hours);
            return h + " ore";
        }
        if (minutes > 60) {
            int hours = minutes / 60;
            int rest = minutes % 60;
            String h = hours == 1 ? "1 ora" : hours + " ore";
            return h + " e " + rest + (rest == 1 ? " minuto" : " minuti");
        }
        return minutes == 1 ? "1 minuto" : minutes + " minuti";
    }

    private JSONArray r36ParseReminderText(String text) {
        JSONArray out = new JSONArray();
        if (text == null || text.trim().isEmpty() || "Nessun avviso".equalsIgnoreCase(text.trim())) return out;
        String raw = text.trim();
        if (raw.matches("[0-9\\s,]+")) {
            for (String part : raw.split(",")) {
                try { out.put(Integer.parseInt(part.trim())); } catch (Exception ignored) {}
            }
            return out;
        }
        java.util.regex.Pattern pattern = java.util.regex.Pattern.compile("([0-9]+(?:[\\.,][0-9]+)?)\\s*(settimana|settimane|giorno|giorni|ora|ore|minuto|minuti)", java.util.regex.Pattern.CASE_INSENSITIVE);
        for (String part : raw.split(";")) {
            java.util.regex.Matcher matcher = pattern.matcher(part.trim());
            if (!matcher.find()) continue;
            try {
                double amount = Double.parseDouble(matcher.group(1).replace(',', '.'));
                String unit = matcher.group(2).toLowerCase(java.util.Locale.ROOT);
                double factor = unit.startsWith("settim") ? 10080d : unit.startsWith("giorn") ? 1440d : unit.startsWith("or") ? 60d : 1d;
                int minutes = (int) Math.round(amount * factor);
                if (minutes >= 0) out.put(minutes);
            } catch (Exception ignored) {}
        }
        return out;
    }

'''
s = s.replace(helper_marker, helpers + helper_marker, 1)

s = s.replace('Android R35 TEST COMPLETO', 'Android R36 TEST COMPLETO')
s = s.replace('Aiuto R35', 'Aiuto R36')
MAIN.write_text(s, encoding='utf-8')

# Version identity.
g = GRADLE.read_text(encoding='utf-8')
require(g, 'versionCode 35', 'versionCode 35')
require(g, "versionName '1.0.0-android-r35-second-factor-choice-fix-test'", 'R35 versionName')
g = g.replace('versionCode 35', 'versionCode 36', 1)
g = g.replace("versionName '1.0.0-android-r35-second-factor-choice-fix-test'", "versionName '1.0.0-android-r36-sync-responsive-graphs-agenda-reminders-test'", 1)
GRADLE.write_text(g, encoding='utf-8')

print('R36 sync, responsive layout, report graphs, agenda source and reminder patch applied')
