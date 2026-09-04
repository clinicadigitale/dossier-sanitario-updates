from pathlib import Path

BASE = Path('android-r3/app/src/main/java/it/dossiersanitario/clinicadigitale/beta')
MAIN = BASE / 'R6MainActivity.java'


def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit(f'R27 core patch failed: missing {label}')
    return text.replace(old, new, 1)

s = MAIN.read_text(encoding='utf-8')

for name in ['renderPanoramica','renderDatiProfilo','renderDocumenti','renderCronologia','renderEsenzioni','renderDiagnosi','renderTerapie','renderMedici','renderConfronta','renderGrafici','renderAgenda','renderMonitoraggio','renderPreferenze']:
    s = replace_once(s, f'    private void {name}() {{', f'    private void {name}R26Legacy() {{', f'rename {name}')

s = s.replace('        profileName = text(profileDisplayName(), 14, TEXT, true);',
              '        profileName = text(r27ProfileDisplayName(), 14, TEXT, true);')
s = replace_once(s, '        page.addView(profileBar);\n\n        LinearLayout topbar = new LinearLayout(this);',
'''        profileBar.setOnClickListener(v -> showR27ProfilePicker());
        page.addView(profileBar);

        LinearLayout topbar = new LinearLayout(this);''', 'profile picker')

start = s.find('    private void loadR26ImportedUiSettings() {')
end = s.find('    private int darkenR26(', start)
if start < 0 or end < 0:
    raise SystemExit('R27 core patch failed: R26 settings loader not found')
loader = r'''    private void loadR26ImportedUiSettings() {
        int base = R27ExactWindows.globalThemeColor(prefs, Color.rgb(23, 138, 114));
        int imported = R27ExactWindows.activeProfileColor(prefs, base);
        GREEN = imported;
        GREEN_DARK = darkenR26(imported, 0.80f);
        r26SessionTimeoutMinutes = prefs.getInt("r26_timeout_override", R26SnapshotBridge.timeoutMinutes(prefs, 15));
    }

'''
s = s[:start] + loader + s[end:]

marker = '    private void renderBackup() {'
if marker not in s:
    raise SystemExit('R27 core patch failed: backup marker missing')

methods = r'''    private String r27ProfileDisplayName() {
        String name = R27ExactWindows.activeProfileName(prefs);
        return name == null || name.trim().isEmpty() ? profileDisplayName() : name;
    }

    private String r27ProfileName(JSONObject p) {
        if (p == null) return "Profilo";
        String name = (p.optString("firstName", "") + " " + p.optString("lastName", "")).trim();
        if (name.isEmpty()) name = p.optString("displayName", p.optString("name", "Profilo"));
        return name;
    }

    private void showR27ProfilePicker() {
        JSONArray profiles = R27ExactWindows.profiles(prefs);
        if (profiles.length() <= 1) {
            Toast.makeText(this, profiles.length() == 0 ? "Nessun altro profilo importato" : "Questo Dossier contiene un solo profilo autorizzato", Toast.LENGTH_SHORT).show();
            return;
        }
        String current = R27ExactWindows.activeProfileId(prefs);
        String[] labels = new String[profiles.length()];
        int selected = 0;
        for (int i = 0; i < profiles.length(); i++) {
            JSONObject p = profiles.optJSONObject(i);
            labels[i] = r27ProfileName(p);
            if (p != null && current.equals(p.optString("id", ""))) selected = i;
        }
        new AlertDialog.Builder(this)
                .setTitle("Cambia profilo")
                .setSingleChoiceItems(labels, selected, (dialog, which) -> {
                    JSONObject p = profiles.optJSONObject(which);
                    if (p == null) return;
                    R27ExactWindows.setActiveProfile(prefs, p.optString("id", ""));
                    loadR26ImportedUiSettings();
                    getWindow().setStatusBarColor(GREEN_DARK);
                    dialog.dismiss();
                    showMainUi(null);
                    renderSection("Panoramica");
                })
                .setNegativeButton("Chiudi", null)
                .show();
    }

    private void renderPanoramica() {
        addReleaseNotice();
        JSONObject p = R27ExactWindows.activeProfile(prefs);
        JSONArray docs = R27ExactWindows.documents(prefs);
        JSONArray therapies = R27ExactWindows.therapies(prefs);
        JSONArray diagnoses = R27ExactWindows.diagnoses(prefs);
        JSONArray events = R27ExactWindows.calendarEvents(prefs);

        LinearLayout summary = card();
        summary.addView(sectionHeader("Riepilogo del profilo"));
        summary.addView(labelValue("Profilo", r27ProfileName(p)));
        summary.addView(labelValue("Documenti totali", String.valueOf(docs.length())));
        summary.addView(labelValue("Terapie registrate", String.valueOf(therapies.length())));
        summary.addView(labelValue("Diagnosi / condizioni", String.valueOf(diagnoses.length())));
        summary.addView(labelValue("Eventi Agenda", String.valueOf(events.length())));
        content.addView(summary, matchWrapBottom(14));

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
            String detail = R27ExactWindows.detail(d);
            if (!detail.isEmpty()) row.addView(text(detail, 12, MUTED, false));
            Button open = compactButton("Apri");
            open.setOnClickListener(v -> R27ExactWindows.openDocument(this, d));
            row.addView(open, matchWrapTop(5));
            recent.addView(row);
        }
        content.addView(recent, matchWrapBottom(14));

        LinearLayout agenda = card();
        agenda.addView(sectionHeader("Agenda"));
        if (events.length() == 0) agenda.addView(text("Nessun evento memorizzato.", 13, MUTED, false));
        for (int i = 0; i < Math.min(events.length(), 6); i++) {
            JSONObject e = events.optJSONObject(i);
            if (e != null) agenda.addView(text(R27ExactWindows.label(e, "Evento") + " · " + R27ExactWindows.detail(e), 13, TEXT, false));
        }
        content.addView(agenda, matchWrapBottom(14));
    }

    private void renderDatiProfilo() {
        JSONObject p = R27ExactWindows.activeProfile(prefs);
        LinearLayout c = card();
        c.addView(sectionHeader("Dati del profilo"));
        if (p == null) c.addView(text("Profilo non disponibile.", 13, MUTED, false));
        else {
            c.addView(labelValue("Nome", p.optString("firstName", "")));
            c.addView(labelValue("Cognome", p.optString("lastName", "")));
            c.addView(labelValue("Data di nascita", p.optString("birthDate", "")));
            c.addView(labelValue("Codice fiscale", p.optString("taxCode", "")));
            c.addView(labelValue("Ruolo", p.optString("relation", "")));
            c.addView(labelValue("E-mail", p.optString("email", "")));
            c.addView(labelValue("Telefono", p.optString("phone", "")));
            c.addView(labelValue("Indirizzo", p.optString("address", "")));
            c.addView(labelValue("CAP", p.optString("postalCode", "")));
            c.addView(labelValue("Città", p.optString("city", "")));
            c.addView(labelValue("Provincia", p.optString("province", "")));
            c.addView(labelValue("Tessera sanitaria", p.optString("healthCard", "")));
            c.addView(labelValue("Scadenza tessera", p.optString("healthCardExpiry", "")));
        }
        content.addView(c, matchWrapBottom(14));
        renderR27HealthCard();
    }

    private void renderR27HealthCard() {
        LinearLayout c = card();
        c.addView(sectionHeader("Tessera Sanitaria"));
        String front = R27ExactWindows.healthFrontPath(prefs);
        String back = R27ExactWindows.healthBackPath(prefs);
        if (front.isEmpty() && back.isEmpty()) c.addView(text("Nessuna immagine della Tessera Sanitaria presente nel backup Windows per questo profilo.", 13, MUTED, false));
        if (!front.isEmpty()) c.addView(r27ImagePreview(front, "Fronte"));
        if (!back.isEmpty()) c.addView(r27ImagePreview(back, "Retro"));
        content.addView(c, matchWrapBottom(14));
    }

    private View r27ImagePreview(String path, String label) {
        LinearLayout box = new LinearLayout(this);
        box.setOrientation(LinearLayout.VERTICAL);
        box.setPadding(0, dp(8), 0, dp(8));
        box.addView(text(label, 13, GREEN_DARK, true));
        Bitmap bitmap = BitmapFactory.decodeFile(path);
        if (bitmap == null) { box.addView(text("Immagine non leggibile", 12, MUTED, false)); return box; }
        ImageView image = new ImageView(this);
        image.setImageBitmap(bitmap);
        image.setAdjustViewBounds(true);
        image.setScaleType(ImageView.ScaleType.FIT_CENTER);
        box.addView(image, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(210)));
        return box;
    }

    private void renderDocumenti() {
        JSONArray docs = R27ExactWindows.documents(prefs);
        LinearLayout intro = card();
        intro.addView(sectionHeader("Documenti"));
        intro.addView(labelValue("Documenti presenti", String.valueOf(docs.length())));
        content.addView(intro, matchWrapBottom(14));
        if (docs.length() == 0) {
            LinearLayout empty = card();
            empty.addView(text("Nessun documento presente.", 13, MUTED, false));
            content.addView(empty, matchWrapBottom(14));
            return;
        }
        JSONArray sorted = R27ExactWindows.recentDocuments(prefs, docs.length());
        for (int i = 0; i < sorted.length(); i++) {
            JSONObject d = sorted.optJSONObject(i);
            if (d == null) continue;
            LinearLayout c = card();
            c.addView(text(R27ExactWindows.label(d, "Documento sanitario"), 16, TEXT, true));
            String detail = R27ExactWindows.detail(d);
            if (!detail.isEmpty()) c.addView(text(detail, 13, GREEN_DARK, true));
            String original = d.optString("originalName", "");
            if (!original.isEmpty()) c.addView(labelValue("File", original));
            String kind = d.optString("documentKind", d.optString("category", ""));
            if (!kind.isEmpty()) c.addView(labelValue("Tipologia", kind));
            Button open = button("Apri documento");
            open.setOnClickListener(v -> R27ExactWindows.openDocument(this, d));
            c.addView(open, matchWrapTop(8));
            content.addView(c, matchWrapBottom(10));
        }
    }

'''
s = s.replace(marker, methods + marker, 1)
MAIN.write_text(s, encoding='utf-8')
print('R27 core UI patch applied')
