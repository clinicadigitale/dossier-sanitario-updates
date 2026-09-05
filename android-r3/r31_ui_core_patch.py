from pathlib import Path

MAIN = Path('android-r3/app/src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java')
s = MAIN.read_text(encoding='utf-8')


def require(text, needle, label):
    if needle not in text:
        raise SystemExit(f'R31 core patch failed: missing {label}')


def replace_method(text, name, replacement):
    sig = f'    private void {name}() {{'
    start = text.find(sig)
    if start < 0:
        raise SystemExit(f'R31 core patch failed: method {name} missing')
    brace = text.find('{', start)
    depth = 0
    end = -1
    for i in range(brace, len(text)):
        if text[i] == '{': depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end < 0:
        raise SystemExit(f'R31 core patch failed: method {name} unclosed')
    return text[:start] + replacement.rstrip() + '\n' + text[end:]

# CheckBox is used by the full therapy/preferences forms.
if 'import android.widget.CheckBox;' not in s:
    require(s, 'import android.widget.Button;\n', 'Button import')
    s = s.replace('import android.widget.Button;\n', 'import android.widget.Button;\nimport android.widget.CheckBox;\n', 1)

# New explicit Emergency section requested by the real-device audit.
require(s, '"Panoramica", "Dati profilo", "Esenzioni", "Documenti", "Cronologia",', 'sections array')
s = s.replace('"Panoramica", "Dati profilo", "Esenzioni", "Documenti", "Cronologia",',
              '"Panoramica", "Dati profilo", "Dati di emergenza", "Esenzioni", "Documenti", "Cronologia",', 1)
require(s, 'case "Dati profilo": renderDatiProfilo(); break;', 'profile switch case')
s = s.replace('case "Dati profilo": renderDatiProfilo(); break;',
              'case "Dati profilo": renderDatiProfilo(); break;\n            case "Dati di emergenza": renderDatiEmergenza(); break;', 1)
require(s, 'case "Dati profilo": return "Dati anagrafici e informazioni strutturate della persona.";', 'profile subtitle')
s = s.replace('case "Dati profilo": return "Dati anagrafici e informazioni strutturate della persona.";',
              'case "Dati profilo": return "Dati anagrafici e informazioni strutturate della persona.";\n            case "Dati di emergenza": return "Contatti e informazioni sanitarie essenziali per le emergenze.";', 1)

panoramica = r'''    private void renderPanoramica() {
        JSONObject p = R27ExactWindows.activeProfile(prefs);
        JSONArray docs = R27ExactWindows.documents(prefs);
        JSONArray therapies = R27ExactWindows.therapies(prefs);
        JSONArray diagnoses = R27ExactWindows.diagnoses(prefs);
        JSONArray events = R27ExactWindows.calendarEvents(prefs);

        LinearLayout profileCard = card();
        profileCard.addView(sectionHeader("Profilo attivo"));
        profileCard.addView(text(r27ProfileName(p), 18, TEXT, true));
        profileCard.addView(text("Tocca il pulsante per passare a un altro profilo autorizzato del Dossier.", 13, MUTED, false), matchWrapTop(4));
        Button switchProfile = button("Cambia utente / profilo");
        switchProfile.setOnClickListener(v -> showR27ProfilePicker());
        profileCard.addView(switchProfile, matchWrapTop(10));
        content.addView(profileCard, matchWrapBottom(14));

        GridLayout grid = new GridLayout(this);
        grid.setColumnCount(2);
        addMetric(grid, "Documenti totali", String.valueOf(docs.length()));
        addMetric(grid, "Terapie registrate", String.valueOf(therapies.length()));
        addMetric(grid, "Diagnosi / condizioni", String.valueOf(diagnoses.length()));
        addMetric(grid, "Eventi Agenda", String.valueOf(events.length()));
        content.addView(grid, matchWrapBottom(14));

        LinearLayout recent = card();
        recent.addView(sectionHeader("Documenti recenti"));
        JSONArray latest = R27ExactWindows.recentDocuments(prefs, 4);
        if (latest.length() == 0) recent.addView(text("Nessun documento presente.", 13, MUTED, false));
        for (int i = 0; i < latest.length(); i++) {
            JSONObject d = latest.optJSONObject(i);
            if (d == null) continue;
            LinearLayout row = new LinearLayout(this);
            row.setOrientation(LinearLayout.VERTICAL);
            row.setPadding(0, dp(7), 0, dp(7));
            row.addView(text(R27ExactWindows.label(d, "Documento"), 14, TEXT, true));
            String date = r31First(d, "clinicalDate", "issueDate", "createdAt", "updatedAt");
            if (!date.isEmpty()) row.addView(labelValue("Data", date));
            Button open = compactButton("Apri");
            open.setOnClickListener(v -> R27ExactWindows.openDocument(this, d));
            row.addView(open, matchWrapTop(5));
            recent.addView(row);
        }
        content.addView(recent, matchWrapBottom(14));

        LinearLayout agenda = card();
        agenda.addView(sectionHeader("Agenda"));
        if (events.length() == 0) agenda.addView(text("Nessun evento memorizzato.", 13, MUTED, false));
        java.util.ArrayList<JSONObject> ordered = r31SortedByDate(events, false, "startDate", "date", "createdAt");
        int shown = Math.min(ordered.size(), 6);
        for (int i = 0; i < shown; i++) {
            JSONObject event = ordered.get(i);
            LinearLayout row = new LinearLayout(this);
            row.setOrientation(LinearLayout.VERTICAL);
            row.setPadding(0, dp(8), 0, dp(8));
            row.addView(text(r31First(event, "title", "name", "category"), 14, TEXT, true));
            row.addView(labelValue("Data", r31Display(event, "startDate", "date")));
            String time = r31First(event, "startTime", "time");
            row.addView(labelValue("Ora", event.optBoolean("allDay", false) || time.isEmpty() ? "Tutto il giorno" : time));
            String category = r31First(event, "category", "type");
            if (!category.isEmpty()) row.addView(labelValue("Tipo", r31CategoryItalian(category)));
            String location = r31First(event, "location", "facility");
            if (!location.isEmpty()) row.addView(labelValue("Luogo", location));
            agenda.addView(row);
        }
        Button agendaOpen = button("Apri Agenda");
        agendaOpen.setOnClickListener(v -> navigateTo("Agenda"));
        agenda.addView(agendaOpen, matchWrapTop(8));
        content.addView(agenda, matchWrapBottom(14));
    }'''
s = replace_method(s, 'renderPanoramica', panoramica)

emergency = r'''    private void renderDatiEmergenza() {
        JSONObject p = R27ExactWindows.activeProfile(prefs);
        LinearLayout c = card();
        c.addView(sectionHeader("Dati di emergenza"));
        if (p == null) {
            c.addView(text("Profilo non disponibile.", 13, MUTED, false));
            content.addView(c, matchWrapBottom(14));
            return;
        }
        r31AddIf(c, "Nominativo contatto", p.optString("emergencyContactName", ""));
        r31AddIf(c, "Rapporto", p.optString("emergencyContactRelation", ""));
        r31AddIf(c, "Telefono contatto", p.optString("emergencyContactPhone", ""));
        r31AddIf(c, "Gruppo sanguigno", p.optString("bloodGroup", ""));
        r31AddIf(c, "Note contatto", p.optString("emergencyContactNotes", ""));
        r31AddIf(c, "Allergie rilevanti", p.optString("emergencyAllergies", ""));
        r31AddIf(c, "Terapie critiche", p.optString("emergencyCriticalTherapies", ""));
        r31AddIf(c, "Condizioni o dispositivi rilevanti", p.optString("emergencyRelevantConditions", ""));
        r31AddIf(c, "Medico di base", p.optString("primaryDoctor", ""));
        r31AddIf(c, "Telefono medico", p.optString("primaryDoctorPhone", ""));
        r31AddIf(c, "E-mail medico", p.optString("primaryDoctorEmail", ""));
        r31AddIf(c, "Note medico", p.optString("primaryDoctorNotes", ""));
        if (r31EmergencyEmpty(p)) c.addView(text("Nessun dato di emergenza registrato.", 13, MUTED, false));
        Button edit = button("Modifica dati di emergenza");
        edit.setOnClickListener(v -> r31EditEmergency(p));
        c.addView(edit, matchWrapTop(12));
        content.addView(c, matchWrapBottom(14));
    }'''
s = replace_method(s, 'renderEsenzioni', r'''    private void renderEsenzioni() {
        JSONArray rows = R27ExactWindows.exemptions(prefs);
        boolean extended = prefs.getBoolean("r31_exemptions_extended", "extended".equalsIgnoreCase(R27ExactWindows.profilePreferences(prefs).optString("exemptionView", "compact")));
        LinearLayout intro = card();
        intro.addView(sectionHeader("Esenzioni"));
        intro.addView(labelValue("Esenzioni registrate", String.valueOf(rows.length())));
        Button mode = button(extended ? "Passa alla vista compatta" : "Passa alla vista estesa");
        mode.setOnClickListener(v -> { prefs.edit().putBoolean("r31_exemptions_extended", !extended).apply(); renderSection("Esenzioni"); });
        intro.addView(mode, matchWrapTop(8));
        content.addView(intro, matchWrapBottom(14));
        for (int i = 0; i < rows.length(); i++) {
            JSONObject row = rows.optJSONObject(i); if (row == null) continue;
            LinearLayout c = card();
            c.addView(text(r31First(row, "code", "description", "name"), 16, TEXT, true));
            String description = row.optString("description", "");
            if (!description.isEmpty() && !description.equals(r31First(row, "code", "description", "name"))) c.addView(labelValue("Descrizione", description));
            String expiry = r31First(row, "expiry", "validTo"); if (!expiry.isEmpty()) c.addView(labelValue("Scadenza", expiry));
            if (extended) {
                r31AddIf(c, "Valida dal", row.optString("validFrom", ""));
                r31AddIf(c, "Ente rilasciante", row.optString("issuer", ""));
                r31AddIf(c, "Limitazioni", row.optString("limitations", ""));
                r31AddIf(c, "Note", row.optString("notes", ""));
                r31AddSourceDocumentButton(c, row);
            }
            content.addView(c, matchWrapBottom(9));
        }
        if (rows.length() == 0) { LinearLayout e = card(); e.addView(text("Nessuna esenzione registrata.", 13, MUTED, false)); content.addView(e, matchWrapBottom(14)); }
    }''')

s = s.replace('    private void renderDatiProfilo() {', '    private void renderDatiProfilo() {', 1)  # freeze: intentionally untouched
# Insert emergency method before the new exemptions implementation.
idx = s.find('    private void renderEsenzioni() {')
if idx < 0: raise SystemExit('R31 core patch failed: exemptions insertion point missing')
s = s[:idx] + emergency + '\n\n' + s[idx:]

documents = r'''    private void renderDocumenti() {
        JSONArray docs = R27ExactWindows.documents(prefs);
        boolean oldestFirst = prefs.getBoolean("r31_documents_oldest_first", false);
        LinearLayout intro = card();
        intro.addView(sectionHeader("Documenti"));
        intro.addView(labelValue("Documenti presenti", String.valueOf(docs.length())));
        Button order = button(oldestFirst ? "Ordine: più vecchi prima" : "Ordine: più recenti prima");
        order.setOnClickListener(v -> { prefs.edit().putBoolean("r31_documents_oldest_first", !oldestFirst).apply(); renderSection("Documenti"); });
        intro.addView(order, matchWrapTop(8));
        content.addView(intro, matchWrapBottom(14));
        java.util.ArrayList<JSONObject> sorted = r31SortedByDate(docs, oldestFirst, "clinicalDate", "issueDate", "createdAt", "updatedAt");
        if (sorted.isEmpty()) { LinearLayout e = card(); e.addView(text("Nessun documento presente.", 13, MUTED, false)); content.addView(e, matchWrapBottom(14)); return; }
        for (JSONObject d : sorted) {
            LinearLayout c = card();
            c.addView(text(R27ExactWindows.label(d, "Documento sanitario"), 16, TEXT, true));
            r31AddIf(c, "Data", r31First(d, "clinicalDate", "issueDate", "createdAt", "updatedAt"));
            r31AddIf(c, "File", d.optString("originalName", ""));
            r31AddIf(c, "Tipologia", r31First(d, "documentKind", "category", "type"));
            Button open = button("Apri documento");
            open.setOnClickListener(v -> R27ExactWindows.openDocument(this, d));
            c.addView(open, matchWrapTop(8));
            content.addView(c, matchWrapBottom(10));
        }
    }'''
s = replace_method(s, 'renderDocumenti', documents)

diagnoses = r'''    private void renderDiagnosi() {
        JSONArray rows = R27ExactWindows.diagnoses(prefs);
        LinearLayout intro = card();
        intro.addView(sectionHeader("Diagnosi"));
        intro.addView(labelValue("Diagnosi / condizioni", String.valueOf(rows.length())));
        content.addView(intro, matchWrapBottom(14));
        if (rows.length() == 0) { LinearLayout e = card(); e.addView(text("Nessuna diagnosi o condizione registrata.", 13, MUTED, false)); content.addView(e, matchWrapBottom(14)); return; }
        for (int i = 0; i < rows.length(); i++) {
            JSONObject row = rows.optJSONObject(i); if (row == null) continue;
            LinearLayout c = card();
            c.addView(text(r31First(row, "name", "diagnosis", "description"), 16, TEXT, true));
            r31AddIf(c, "Data", r31First(row, "date", "diagnosisDate", "createdAt"));
            r31AddIf(c, "Categoria", r31First(row, "category", "type"));
            r31AddIf(c, "Stato", r31StatusItalian(row.optString("status", "")));
            r31AddIf(c, "Specializzazione", r31First(row, "specialty", "specialization"));
            r31AddIf(c, "Struttura", r31First(row, "facility", "structure"));
            r31AddIf(c, "Note ed evoluzione", r31First(row, "notes", "evolution", "details"));
            r31AddSourceDocumentButton(c, row);
            content.addView(c, matchWrapBottom(9));
        }
    }'''
s = replace_method(s, 'renderDiagnosi', diagnoses)

therapies = r'''    private void renderTerapie() {
        JSONArray rows = R27ExactWindows.therapies(prefs);
        LinearLayout intro = card();
        intro.addView(sectionHeader("Terapie"));
        intro.addView(labelValue("Terapie registrate", String.valueOf(rows.length())));
        Button add = button("Aggiungi terapia"); add.setOnClickListener(v -> r31EditTherapy(null)); intro.addView(add, matchWrapTop(8));
        content.addView(intro, matchWrapBottom(14));
        if (rows.length() == 0) { LinearLayout e = card(); e.addView(text("Nessuna terapia registrata.", 13, MUTED, false)); content.addView(e, matchWrapBottom(14)); return; }
        for (int i = 0; i < rows.length(); i++) {
            JSONObject row = rows.optJSONObject(i); if (row == null) continue;
            LinearLayout c = card();
            c.addView(text(r31First(row, "medication", "farmaco", "name"), 16, TEXT, true));
            r31AddIf(c, "Orario", r31First(row, "time", "times"));
            r31AddIf(c, "Principio attivo", row.optString("activeIngredient", ""));
            r31AddIf(c, "Dosaggio", row.optString("dosage", ""));
            r31AddIf(c, "Frequenza / modalità", row.optString("frequency", ""));
            r31AddIf(c, "Stato", r31StatusItalian(row.has("active") ? (row.optBoolean("active", true) ? "active" : "inactive") : row.optString("status", "")));
            r31AddSourceDocumentButton(c, row);
            Button edit = button("Modifica terapia"); edit.setOnClickListener(v -> r31EditTherapy(row)); c.addView(edit, matchWrapTop(8));
            content.addView(c, matchWrapBottom(10));
        }
    }'''
s = replace_method(s, 'renderTerapie', therapies)

doctors = r'''    private void renderMedici() {
        JSONArray rows = R27ExactWindows.doctors(prefs);
        LinearLayout intro = card();
        intro.addView(sectionHeader("Medici e specialisti"));
        intro.addView(labelValue("Contatti registrati", String.valueOf(rows.length())));
        Button add = button("Aggiungi medico"); add.setOnClickListener(v -> r31EditDoctor(null)); intro.addView(add, matchWrapTop(8));
        content.addView(intro, matchWrapBottom(14));
        if (rows.length() == 0) { LinearLayout e = card(); e.addView(text("Nessun medico o specialista registrato.", 13, MUTED, false)); content.addView(e, matchWrapBottom(14)); return; }
        for (int i = 0; i < rows.length(); i++) {
            JSONObject row = rows.optJSONObject(i); if (row == null) continue;
            LinearLayout c = card();
            c.addView(text(r31First(row, "name", "displayName"), 16, TEXT, true));
            r31AddIf(c, "Specializzazione", r31First(row, "role", "specialty"));
            r31AddIf(c, "Telefono", row.optString("phone", ""));
            r31AddIf(c, "E-mail", row.optString("email", ""));
            r31AddIf(c, "Struttura", row.optString("facility", ""));
            r31AddIf(c, "Note", row.optString("notes", ""));
            Button edit = compactButton("Modifica"); edit.setOnClickListener(v -> r31EditDoctor(row)); c.addView(edit, matchWrapTop(7));
            content.addView(c, matchWrapBottom(9));
        }
    }'''
s = replace_method(s, 'renderMedici', doctors)

# Shared R31 core helpers and complete edit windows.
insert = '    private void renderBackup() {'
require(s, insert, 'renderBackup insertion point')
helpers = r'''    private void r31AddIf(LinearLayout parent, String label, String value) {
        if (parent == null || value == null || value.trim().isEmpty()) return;
        parent.addView(labelValue(label, value.trim()));
    }

    private String r31First(JSONObject row, String... keys) {
        if (row == null) return "";
        for (String key : keys) { String value = row.optString(key, "").trim(); if (!value.isEmpty()) return value; }
        return "";
    }

    private String r31Display(JSONObject row, String... keys) {
        String value = r31First(row, keys); return value.isEmpty() ? "Non indicata" : value;
    }

    private java.util.ArrayList<JSONObject> r31SortedByDate(JSONArray source, boolean oldestFirst, String... keys) {
        java.util.ArrayList<JSONObject> list = new java.util.ArrayList<>();
        if (source != null) for (int i = 0; i < source.length(); i++) if (source.optJSONObject(i) != null) list.add(source.optJSONObject(i));
        list.sort((a,b) -> { String da = r31First(a, keys), db = r31First(b, keys); int cmp = da.compareTo(db); return oldestFirst ? cmp : -cmp; });
        return list;
    }

    private String r31StatusItalian(String raw) {
        String s = raw == null ? "" : raw.trim().toLowerCase(Locale.ROOT);
        if (s.isEmpty()) return "";
        if ("active".equals(s) || "attiva".equals(s) || "confirmed".equals(s)) return "Attiva";
        if ("inactive".equals(s) || "closed".equals(s) || "resolved".equals(s)) return "Conclusa / non attiva";
        if ("planned".equals(s) || "scheduled".equals(s) || "programmato".equals(s)) return "Programmata";
        if ("completed".equals(s) || "completato".equals(s)) return "Completata";
        if ("cancelled".equals(s) || "canceled".equals(s) || "annullato".equals(s)) return "Annullata";
        if ("pending".equals(s) || "to_verify".equals(s)) return "Da verificare";
        return raw;
    }

    private String r31CategoryItalian(String raw) {
        String s = raw == null ? "" : raw.trim().toLowerCase(Locale.ROOT);
        if ("visit".equals(s) || "visita".equals(s)) return "Visita";
        if ("exam".equals(s) || "esame".equals(s)) return "Esame";
        if ("renewal".equals(s) || "rinnovo".equals(s)) return "Rinnovo";
        if ("request".equals(s) || "richiesta".equals(s)) return "Richiesta";
        return raw;
    }

    private void r31AddSourceDocumentButton(LinearLayout parent, JSONObject row) {
        String id = row == null ? "" : row.optString("sourceDocumentId", "").trim();
        if (id.isEmpty()) return;
        JSONObject doc = R27ExactWindows.documentById(prefs, id);
        if (doc == null) return;
        Button source = compactButton("Apri documento di riferimento");
        source.setOnClickListener(v -> R27ExactWindows.openDocument(this, doc));
        parent.addView(source, matchWrapTop(7));
    }

    private boolean r31EmergencyEmpty(JSONObject p) {
        String[] keys = {"emergencyContactName","emergencyContactRelation","emergencyContactPhone","bloodGroup","emergencyContactNotes","emergencyAllergies","emergencyCriticalTherapies","emergencyRelevantConditions","primaryDoctor","primaryDoctorPhone","primaryDoctorEmail","primaryDoctorNotes"};
        for (String key : keys) if (!p.optString(key, "").trim().isEmpty()) return false;
        return true;
    }

    private void r31EditEmergency(JSONObject source) {
        if (source == null) return;
        LinearLayout form = new LinearLayout(this); form.setOrientation(LinearLayout.VERTICAL); form.setPadding(dp(16), dp(8), dp(16), dp(8));
        EditText name = field("Nominativo contatto", source.optString("emergencyContactName", ""));
        EditText relation = field("Rapporto", source.optString("emergencyContactRelation", ""));
        EditText phone = field("Telefono contatto", source.optString("emergencyContactPhone", ""));
        EditText blood = field("Gruppo sanguigno", source.optString("bloodGroup", ""));
        EditText contactNotes = field("Note contatto di emergenza", source.optString("emergencyContactNotes", ""));
        EditText allergies = field("Allergie rilevanti", source.optString("emergencyAllergies", ""));
        EditText critical = field("Terapie critiche", source.optString("emergencyCriticalTherapies", ""));
        EditText conditions = field("Condizioni o dispositivi rilevanti", source.optString("emergencyRelevantConditions", ""));
        EditText doctor = field("Medico di base", source.optString("primaryDoctor", ""));
        EditText doctorPhone = field("Telefono medico", source.optString("primaryDoctorPhone", ""));
        EditText doctorEmail = field("E-mail medico", source.optString("primaryDoctorEmail", ""));
        EditText doctorNotes = field("Note medico", source.optString("primaryDoctorNotes", ""));
        for (EditText e : new EditText[]{name,relation,phone,blood,contactNotes,allergies,critical,conditions,doctor,doctorPhone,doctorEmail,doctorNotes}) form.addView(e);
        ScrollView scroll = new ScrollView(this); scroll.addView(form);
        new AlertDialog.Builder(this).setTitle("Modifica dati di emergenza").setView(scroll).setNegativeButton("Annulla", null).setPositiveButton("Salva", (d,w) -> {
            try {
                JSONObject updated = new JSONObject(source.toString());
                updated.put("emergencyContactName", clean(name)); updated.put("emergencyContactRelation", clean(relation)); updated.put("emergencyContactPhone", clean(phone));
                updated.put("bloodGroup", clean(blood)); updated.put("emergencyContactNotes", clean(contactNotes)); updated.put("emergencyAllergies", clean(allergies));
                updated.put("emergencyCriticalTherapies", clean(critical)); updated.put("emergencyRelevantConditions", clean(conditions));
                updated.put("primaryDoctor", clean(doctor)); updated.put("primaryDoctorPhone", clean(doctorPhone)); updated.put("primaryDoctorEmail", clean(doctorEmail)); updated.put("primaryDoctorNotes", clean(doctorNotes));
                String legacy = (clean(name) + (clean(phone).isEmpty() ? "" : " · " + clean(phone))).trim(); updated.put("emergencyContact", legacy);
                R27ExactWindows.updateActiveProfile(prefs, updated); R12CloudManager.queueR31EntityPut(this, prefs, "profiles", updated); renderSection("Dati di emergenza");
            } catch (Exception failure) { Toast.makeText(this, "Salvataggio non riuscito", Toast.LENGTH_LONG).show(); }
        }).show();
    }

    private CheckBox r31Check(String label, boolean checked) {
        CheckBox c = new CheckBox(this); c.setText(label); c.setChecked(checked); c.setTextColor(TEXT); c.setPadding(0, dp(5), 0, dp(5)); return c;
    }

    private void r31EditTherapy(JSONObject source) {
        JSONObject base = source == null ? new JSONObject() : source;
        LinearLayout form = new LinearLayout(this); form.setOrientation(LinearLayout.VERTICAL); form.setPadding(dp(16), dp(8), dp(16), dp(10));
        EditText time = field("Orario/i", base.optString("time", ""));
        EditText medication = field("Farmaco", r31First(base, "medication", "farmaco", "name"));
        EditText ingredient = field("Principio attivo", base.optString("activeIngredient", ""));
        EditText manufacturer = field("Produttore / Marca", base.optString("manufacturer", ""));
        EditText medicineType = field("Tipo", base.optString("medicineType", ""));
        EditText dosage = field("Dosaggio", base.optString("dosage", ""));
        EditText frequency = field("Frequenza e modalità", base.optString("frequency", ""));
        EditText period = field("Validità / aggiornamento", base.optString("period", ""));
        EditText effective = field("Decorrenza modifica piano", base.optString("planEffectiveDate", ""));
        EditText packUnits = field("Unità nella confezione", base.optString("packUnits", ""));
        EditText packCount = field("Numero confezioni disponibili", base.optString("packCount", ""));
        EditText dailyUnits = field("Unità assunte per giorno di assunzione", base.optString("dailyUnits", ""));
        EditText packStart = field("Data inizio confezione", base.optString("packStartDate", ""));
        EditText notes = field("Note", base.optString("notes", ""));
        for (EditText e : new EditText[]{time,medication,ingredient,manufacturer,medicineType,dosage,frequency,period,effective,packUnits,packCount,dailyUnits,packStart,notes}) form.addView(e);
        form.addView(text("Giorni di assunzione", 14, TEXT, true), matchWrapTop(8));
        JSONObject days = base.optJSONObject("therapyDays"); if (days == null) days = new JSONObject();
        String[] dk={"mon","tue","wed","thu","fri","sat","sun"}; String[] dl={"Lun","Mar","Mer","Gio","Ven","Sab","Dom"}; CheckBox[] dc=new CheckBox[7];
        for(int i=0;i<7;i++){dc[i]=r31Check(dl[i],days.optBoolean(dk[i],false));form.addView(dc[i]);}
        CheckBox active = r31Check("Terapia attiva", base.has("active") ? base.optBoolean("active", true) : !"inactive".equalsIgnoreCase(base.optString("status", "")));
        CheckBox reorder = r31Check("Gestisci scorta e riordino", base.optBoolean("reorderEnabled", false)); form.addView(active); form.addView(reorder);
        ScrollView scroll = new ScrollView(this); scroll.addView(form);
        new AlertDialog.Builder(this).setTitle(source == null ? "Nuova terapia" : "Modifica terapia").setView(scroll).setNegativeButton("Annulla", null).setPositiveButton("Salva", (d,w) -> {
            try {
                JSONObject updated = new JSONObject(base.toString());
                if (updated.optString("id", "").isEmpty()) updated.put("id", "therapy_android_" + System.currentTimeMillis());
                updated.put("profileId", R27ExactWindows.activeProfileId(prefs)); updated.put("time", clean(time)); updated.put("medication", clean(medication)); updated.put("activeIngredient", clean(ingredient));
                updated.put("manufacturer", clean(manufacturer)); updated.put("medicineType", clean(medicineType)); updated.put("dosage", clean(dosage)); updated.put("frequency", clean(frequency)); updated.put("period", clean(period));
                updated.put("planEffectiveDate", clean(effective)); updated.put("packUnits", clean(packUnits)); updated.put("packCount", clean(packCount)); updated.put("dailyUnits", clean(dailyUnits)); updated.put("packStartDate", clean(packStart)); updated.put("notes", clean(notes));
                JSONObject outDays = new JSONObject(); for(int i=0;i<7;i++) outDays.put(dk[i], dc[i].isChecked()); updated.put("therapyDays", outDays); updated.put("active", active.isChecked()); updated.put("reorderEnabled", reorder.isChecked());
                if (!R27ExactWindows.upsertData(prefs, "therapies", updated)) throw new Exception("dati non salvati");
                R12CloudManager.queueR31EntityPut(this, prefs, "therapies", updated); renderSection("Terapie");
            } catch (Exception failure) { Toast.makeText(this, "Salvataggio terapia non riuscito", Toast.LENGTH_LONG).show(); }
        }).show();
    }

    private void r31EditDoctor(JSONObject source) {
        JSONObject base = source == null ? new JSONObject() : source;
        LinearLayout form = new LinearLayout(this); form.setOrientation(LinearLayout.VERTICAL); form.setPadding(dp(16), dp(8), dp(16), dp(8));
        EditText name=field("Nome e cognome",base.optString("name","")); EditText role=field("Specializzazione",r31First(base,"role","specialty")); EditText email=field("E-mail",base.optString("email","")); EditText phone=field("Telefono",base.optString("phone","")); EditText facility=field("Struttura",base.optString("facility","")); EditText notes=field("Note",base.optString("notes",""));
        for(EditText e:new EditText[]{name,role,email,phone,facility,notes})form.addView(e); ScrollView scroll=new ScrollView(this);scroll.addView(form);
        new AlertDialog.Builder(this).setTitle(source==null?"Aggiungi medico":"Modifica medico").setView(scroll).setNegativeButton("Annulla",null).setPositiveButton("Salva",(d,w)->{
            try{JSONObject updated=new JSONObject(base.toString());if(updated.optString("id","").isEmpty())updated.put("id","doctor_android_"+System.currentTimeMillis());updated.put("profileId",R27ExactWindows.activeProfileId(prefs));updated.put("name",clean(name));updated.put("role",clean(role));updated.put("specialty",clean(role));updated.put("email",clean(email));updated.put("phone",clean(phone));updated.put("facility",clean(facility));updated.put("notes",clean(notes));if(!R27ExactWindows.upsertData(prefs,"doctors",updated))throw new Exception("dati non salvati");R12CloudManager.queueR31EntityPut(this,prefs,"doctors",updated);renderSection("Medici e specialisti");}catch(Exception failure){Toast.makeText(this,"Salvataggio medico non riuscito",Toast.LENGTH_LONG).show();}
        }).show();
    }

'''
s = s.replace(insert, helpers + insert, 1)

# Visible version label only; no release/debug notice is rendered on Panoramica anymore.
s = s.replace('Android R30 TEST COMPLETO', 'Android R31 TEST COMPLETO')
s = s.replace('Aiuto R30', 'Aiuto R31')
s = s.replace('R30: sezione completa collegata al backup Windows', 'R31: sezione mobile completa collegata al Dossier Windows')
MAIN.write_text(s, encoding='utf-8')
print('R31 home, emergency and clinical core UI patch applied')
