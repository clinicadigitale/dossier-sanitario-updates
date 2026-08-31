from pathlib import Path

BASE = Path('android-r3/app/src/main/java/it/dossiersanitario/clinicadigitale/beta')
MAIN = BASE / 'R6MainActivity.java'
EDITOR = BASE / 'DocumentEditorActivity.java'


def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit(f'R8 patch failed: missing {label}')
    return text.replace(old, new, 1)


def patch_main():
    s = MAIN.read_text(encoding='utf-8')

    s = replace_once(
        s,
        'import android.widget.Toast;\n\nimport java.io.File;',
        'import android.widget.Toast;\n\nimport org.json.JSONArray;\nimport org.json.JSONObject;\n\nimport java.io.File;',
        'main JSON imports'
    )

    s = replace_once(
        s,
        '    private static final String PREFS = "clinica_android_beta";\n',
        '    private static final String PREFS = "clinica_android_beta";\n'
        '    private static final String PREF_EXEMPTIONS = "android_exemptions_json";\n'
        '    private static final String PREF_DOCTORS = "android_doctors_json";\n'
        '    private static final String PREF_EVENTS = "android_history_json";\n',
        'main preference constants'
    )

    s = replace_once(
        s,
        '    private long lastPanoramicaBackMs = 0L;\n',
        '    private long lastPanoramicaBackMs = 0L;\n'
        '    private boolean pendingEditorNewCapture = false;\n',
        'main editor state'
    )

    old_switch = '''            case "Panoramica": renderPanoramica(); break;\n            case "Dati profilo": renderDatiProfilo(); break;\n            case "Documenti": renderDocumenti(); break;\n            case "Monitoraggio": renderMonitoraggio(); break;'''
    new_switch = '''            case "Panoramica": renderPanoramica(); break;\n            case "Dati profilo": renderDatiProfilo(); break;\n            case "Esenzioni": renderEsenzioni(); break;\n            case "Documenti": renderDocumenti(); break;\n            case "Cronologia": renderCronologia(); break;\n            case "Medici e specialisti": renderMedici(); break;\n            case "Monitoraggio": renderMonitoraggio(); break;'''
    s = replace_once(s, old_switch, new_switch, 'main section switch')

    old_sub = '''            case "Dati profilo": return "Dati anagrafici e informazioni strutturate della persona.";\n            case "Documenti": return "Archivio privato e scanner documentale integrato.";'''
    new_sub = '''            case "Dati profilo": return "Dati anagrafici e informazioni strutturate della persona.";\n            case "Esenzioni": return "Esenzioni sanitarie del profilo, salvate localmente.";\n            case "Documenti": return "Archivio privato e scanner documentale integrato.";\n            case "Cronologia": return "Attività e modifiche rilevanti registrate nel Dossier locale.";\n            case "Medici e specialisti": return "Medici e specialisti di riferimento del profilo.";'''
    s = replace_once(s, old_sub, new_sub, 'main subtitles')

    s = replace_once(
        s,
        '        addMetric(grid, "Ultimo evento", "Nessuno");',
        '        addMetric(grid, "Ultimo evento", latestEventSummary());',
        'panoramica latest event'
    )

    s = replace_once(
        s,
        '            profileName.setText(profileDisplayName());\n            Toast.makeText(this, "Dati profilo salvati", Toast.LENGTH_SHORT).show();',
        '            profileName.setText(profileDisplayName());\n            logEvent("Dati profilo aggiornati");\n            Toast.makeText(this, "Dati profilo salvati", Toast.LENGTH_SHORT).show();',
        'profile history log'
    )

    old_result = '''        if (requestCode == EDIT_DOCUMENT) {\n            cleanCameraTemp();\n            if ("Documenti".equals(currentSection)) refreshDocumentState();\n            if (resultCode == RESULT_OK) {\n                Toast.makeText(this, "Documento salvato nel Dossier", Toast.LENGTH_SHORT).show();\n            }\n        }'''
    new_result = '''        if (requestCode == EDIT_DOCUMENT) {\n            cleanCameraTemp();\n            if ("Documenti".equals(currentSection)) refreshDocumentState();\n            if (resultCode == RESULT_OK) {\n                logEvent(pendingEditorNewCapture ? "Nuovo documento fotografico salvato" : "Documento fotografico modificato");\n                Toast.makeText(this, "Documento salvato nel Dossier", Toast.LENGTH_SHORT).show();\n            }\n            pendingEditorNewCapture = false;\n        }'''
    s = replace_once(s, old_result, new_result, 'document history log')

    s = replace_once(
        s,
        '    private void launchEditor(File source, boolean newCapture) {\n        Intent intent = new Intent(this, DocumentEditorActivity.class);',
        '    private void launchEditor(File source, boolean newCapture) {\n        pendingEditorNewCapture = newCapture;\n        Intent intent = new Intent(this, DocumentEditorActivity.class);',
        'editor launch state'
    )

    insert_marker = '    private void renderMonitoraggio() {'
    if insert_marker not in s:
        raise SystemExit('R8 patch failed: missing monitoraggio insertion point')

    modules = r'''
    private void renderEsenzioni() {
        LinearLayout intro = card();
        intro.addView(sectionHeader("Esenzioni"));
        intro.addView(text("Le esenzioni vengono salvate nel Dossier locale del profilo. Non viene richiesto alcun accesso ai dati del telefono.", 13, MUTED, false));
        Button add = button("Aggiungi esenzione");
        add.setOnClickListener(v -> showExemptionDialog(null));
        intro.addView(add, matchWrapTop(10));
        content.addView(intro, matchWrapBottom(14));

        JSONArray items = readArray(PREF_EXEMPTIONS);
        if (items.length() == 0) {
            LinearLayout empty = card();
            empty.addView(text("Nessuna esenzione registrata.", 14, MUTED, false));
            content.addView(empty, matchWrapBottom(14));
            return;
        }

        for (int i = 0; i < items.length(); i++) {
            JSONObject item = items.optJSONObject(i);
            if (item == null) continue;
            long id = item.optLong("id", 0L);
            LinearLayout c = card();
            String code = item.optString("code", "").trim();
            String desc = item.optString("description", "").trim();
            c.addView(text(code.isEmpty() ? "Esenzione" : code, 17, TEXT, true));
            if (!desc.isEmpty()) c.addView(text(desc, 14, TEXT, false));
            String expiry = item.optString("expiry", "").trim();
            if (!expiry.isEmpty()) c.addView(labelValue("Scadenza", expiry));
            String notes = item.optString("notes", "").trim();
            if (!notes.isEmpty()) c.addView(labelValue("Note", notes));

            LinearLayout actions = new LinearLayout(this);
            actions.setOrientation(LinearLayout.HORIZONTAL);
            actions.setPadding(0, dp(9), 0, 0);
            Button edit = compactButton("Modifica");
            edit.setOnClickListener(v -> showExemptionDialog(item));
            actions.addView(edit, new LinearLayout.LayoutParams(0, dp(42), 1f));
            Button del = compactButton("Elimina");
            LinearLayout.LayoutParams dpv = new LinearLayout.LayoutParams(0, dp(42), 1f);
            dpv.setMargins(dp(7), 0, 0, 0);
            del.setOnClickListener(v -> confirmDeleteRecord(PREF_EXEMPTIONS, id, "Eliminare questa esenzione?", "Esenzione eliminata", "Esenzioni"));
            actions.addView(del, dpv);
            c.addView(actions);
            content.addView(c, matchWrapBottom(12));
        }
    }

    private void showExemptionDialog(JSONObject existing) {
        LinearLayout form = dialogForm();
        EditText code = field("Codice esenzione", existing == null ? "" : existing.optString("code", ""));
        EditText description = field("Descrizione", existing == null ? "" : existing.optString("description", ""));
        EditText expiry = field("Scadenza (gg/mm/aaaa)", existing == null ? "" : existing.optString("expiry", ""));
        EditText notes = field("Note", existing == null ? "" : existing.optString("notes", ""));
        form.addView(code); form.addView(description); form.addView(expiry); form.addView(notes);

        new AlertDialog.Builder(this)
                .setTitle(existing == null ? "Nuova esenzione" : "Modifica esenzione")
                .setView(form)
                .setNegativeButton("Annulla", null)
                .setPositiveButton("Salva", (d, w) -> {
                    String c = clean(code);
                    if (c.isEmpty()) {
                        Toast.makeText(this, "Inserisci almeno il codice dell'esenzione", Toast.LENGTH_LONG).show();
                        return;
                    }
                    try {
                        long id = existing == null ? System.currentTimeMillis() : existing.optLong("id", System.currentTimeMillis());
                        JSONObject obj = new JSONObject();
                        obj.put("id", id);
                        obj.put("code", c);
                        obj.put("description", clean(description));
                        obj.put("expiry", clean(expiry));
                        obj.put("notes", clean(notes));
                        upsertRecord(PREF_EXEMPTIONS, obj);
                        logEvent(existing == null ? "Esenzione aggiunta: " + c : "Esenzione aggiornata: " + c);
                        renderSection("Esenzioni");
                    } catch (Exception e) {
                        Toast.makeText(this, "Salvataggio esenzione non riuscito", Toast.LENGTH_LONG).show();
                    }
                })
                .show();
    }

    private void renderMedici() {
        LinearLayout intro = card();
        intro.addView(sectionHeader("Medici e specialisti"));
        intro.addView(text("Rubrica sanitaria privata del profilo. I dati restano nel Dossier e non vengono letti o copiati dalla rubrica del telefono.", 13, MUTED, false));
        Button add = button("Aggiungi medico o specialista");
        add.setOnClickListener(v -> showDoctorDialog(null));
        intro.addView(add, matchWrapTop(10));
        content.addView(intro, matchWrapBottom(14));

        JSONArray items = readArray(PREF_DOCTORS);
        if (items.length() == 0) {
            LinearLayout empty = card();
            empty.addView(text("Nessun medico o specialista registrato.", 14, MUTED, false));
            content.addView(empty, matchWrapBottom(14));
            return;
        }

        for (int i = 0; i < items.length(); i++) {
            JSONObject item = items.optJSONObject(i);
            if (item == null) continue;
            long id = item.optLong("id", 0L);
            LinearLayout c = card();
            c.addView(text(item.optString("name", "Medico"), 17, TEXT, true));
            String specialty = item.optString("specialty", "").trim();
            if (!specialty.isEmpty()) c.addView(text(specialty, 14, GREEN_DARK, true));
            String phone = item.optString("phone", "").trim();
            String email = item.optString("email", "").trim();
            String notes = item.optString("notes", "").trim();
            if (!phone.isEmpty()) c.addView(labelValue("Telefono", phone));
            if (!email.isEmpty()) c.addView(labelValue("Email", email));
            if (!notes.isEmpty()) c.addView(labelValue("Note", notes));

            LinearLayout actions = new LinearLayout(this);
            actions.setOrientation(LinearLayout.HORIZONTAL);
            actions.setPadding(0, dp(9), 0, 0);
            Button edit = compactButton("Modifica");
            edit.setOnClickListener(v -> showDoctorDialog(item));
            actions.addView(edit, new LinearLayout.LayoutParams(0, dp(42), 1f));
            Button del = compactButton("Elimina");
            LinearLayout.LayoutParams dpv = new LinearLayout.LayoutParams(0, dp(42), 1f);
            dpv.setMargins(dp(7), 0, 0, 0);
            del.setOnClickListener(v -> confirmDeleteRecord(PREF_DOCTORS, id, "Eliminare questo medico o specialista?", "Medico/specialista eliminato", "Medici e specialisti"));
            actions.addView(del, dpv);
            c.addView(actions);
            content.addView(c, matchWrapBottom(12));
        }
    }

    private void showDoctorDialog(JSONObject existing) {
        LinearLayout form = dialogForm();
        EditText name = field("Nome e cognome", existing == null ? "" : existing.optString("name", ""));
        EditText specialty = field("Specializzazione", existing == null ? "" : existing.optString("specialty", ""));
        EditText phone = field("Telefono", existing == null ? "" : existing.optString("phone", ""));
        EditText email = field("Email", existing == null ? "" : existing.optString("email", ""));
        EditText notes = field("Note", existing == null ? "" : existing.optString("notes", ""));
        form.addView(name); form.addView(specialty); form.addView(phone); form.addView(email); form.addView(notes);

        new AlertDialog.Builder(this)
                .setTitle(existing == null ? "Nuovo medico o specialista" : "Modifica medico o specialista")
                .setView(form)
                .setNegativeButton("Annulla", null)
                .setPositiveButton("Salva", (d, w) -> {
                    String n = clean(name);
                    if (n.isEmpty()) {
                        Toast.makeText(this, "Inserisci almeno il nome", Toast.LENGTH_LONG).show();
                        return;
                    }
                    try {
                        long id = existing == null ? System.currentTimeMillis() : existing.optLong("id", System.currentTimeMillis());
                        JSONObject obj = new JSONObject();
                        obj.put("id", id);
                        obj.put("name", n);
                        obj.put("specialty", clean(specialty));
                        obj.put("phone", clean(phone));
                        obj.put("email", clean(email));
                        obj.put("notes", clean(notes));
                        upsertRecord(PREF_DOCTORS, obj);
                        logEvent(existing == null ? "Medico/specialista aggiunto: " + n : "Medico/specialista aggiornato: " + n);
                        renderSection("Medici e specialisti");
                    } catch (Exception e) {
                        Toast.makeText(this, "Salvataggio non riuscito", Toast.LENGTH_LONG).show();
                    }
                })
                .show();
    }

    private void renderCronologia() {
        LinearLayout intro = card();
        intro.addView(sectionHeader("Cronologia locale"));
        intro.addView(text("Registra le principali modifiche effettuate nel Dossier Android. La cronologia resta nello spazio privato dell'app.", 13, MUTED, false));
        content.addView(intro, matchWrapBottom(14));

        JSONArray events = readArray(PREF_EVENTS);
        if (events.length() == 0) {
            LinearLayout empty = card();
            empty.addView(text("Nessun evento registrato dalla R8 in poi.", 14, MUTED, false));
            content.addView(empty, matchWrapBottom(14));
            return;
        }

        SimpleDateFormat fmt = new SimpleDateFormat("dd/MM/yyyy HH:mm", Locale.ITALY);
        int limit = Math.min(events.length(), 40);
        for (int i = 0; i < limit; i++) {
            JSONObject e = events.optJSONObject(i);
            if (e == null) continue;
            LinearLayout c = card();
            c.addView(text(e.optString("text", "Evento"), 14, TEXT, true));
            c.addView(text(fmt.format(new Date(e.optLong("time", 0L))), 12, MUTED, false));
            content.addView(c, matchWrapBottom(8));
        }
    }

    private LinearLayout dialogForm() {
        LinearLayout form = new LinearLayout(this);
        form.setOrientation(LinearLayout.VERTICAL);
        form.setPadding(dp(18), dp(6), dp(18), 0);
        return form;
    }

    private JSONArray readArray(String key) {
        try {
            String raw = prefs.getString(key, "[]");
            return new JSONArray(raw == null || raw.trim().isEmpty() ? "[]" : raw);
        } catch (Exception e) {
            return new JSONArray();
        }
    }

    private void saveArray(String key, JSONArray array) {
        prefs.edit().putString(key, array.toString()).apply();
    }

    private void upsertRecord(String key, JSONObject object) throws Exception {
        JSONArray array = readArray(key);
        long id = object.optLong("id", 0L);
        boolean replaced = false;
        for (int i = 0; i < array.length(); i++) {
            JSONObject current = array.optJSONObject(i);
            if (current != null && current.optLong("id", -1L) == id) {
                array.put(i, object);
                replaced = true;
                break;
            }
        }
        if (!replaced) array.put(object);
        saveArray(key, array);
    }

    private void confirmDeleteRecord(String key, long id, String question, String eventText, String returnSection) {
        new AlertDialog.Builder(this)
                .setTitle("Conferma eliminazione")
                .setMessage(question)
                .setNegativeButton("Annulla", null)
                .setPositiveButton("Elimina", (d, w) -> {
                    JSONArray array = readArray(key);
                    for (int i = array.length() - 1; i >= 0; i--) {
                        JSONObject obj = array.optJSONObject(i);
                        if (obj != null && obj.optLong("id", -1L) == id) array.remove(i);
                    }
                    saveArray(key, array);
                    logEvent(eventText);
                    renderSection(returnSection);
                })
                .show();
    }

    private void logEvent(String text) {
        if (text == null || text.trim().isEmpty()) return;
        try {
            JSONArray old = readArray(PREF_EVENTS);
            JSONArray next = new JSONArray();
            JSONObject event = new JSONObject();
            event.put("time", System.currentTimeMillis());
            event.put("text", text.trim());
            next.put(event);
            int keep = Math.min(old.length(), 79);
            for (int i = 0; i < keep; i++) {
                JSONObject previous = old.optJSONObject(i);
                if (previous != null) next.put(previous);
            }
            saveArray(PREF_EVENTS, next);
        } catch (Exception ignored) { }
    }

    private String latestEventSummary() {
        JSONArray events = readArray(PREF_EVENTS);
        JSONObject event = events.optJSONObject(0);
        if (event == null) return "Nessuno";
        String text = event.optString("text", "Nessuno").trim();
        if (text.length() > 32) text = text.substring(0, 29) + "…";
        return text.isEmpty() ? "Nessuno" : text;
    }

'''
    s = s.replace(insert_marker, modules + insert_marker, 1)

    visible_replacements = {
        'Android R6 TEST': 'Android R8 TEST',
        'Aiuto R6': 'Aiuto R8',
        'R6: struttura presente': 'R8: struttura presente',
        'R6 mantiene lo stesso pacchetto Android': 'R8 mantiene lo stesso pacchetto Android',
        'Installala sopra la R5': 'Installala sopra la R7',
        'Importazione file non ancora attiva nella R6': 'Importazione file non ancora attiva nella R8'
    }
    for old, new in visible_replacements.items():
        s = s.replace(old, new)

    MAIN.write_text(s, encoding='utf-8')


def patch_editor():
    s = EDITOR.read_text(encoding='utf-8')

    s = replace_once(
        s,
        'import android.widget.Button;\nimport android.widget.LinearLayout;',
        'import android.widget.Button;\nimport android.widget.HorizontalScrollView;\nimport android.widget.LinearLayout;',
        'editor horizontal scroll import'
    )

    start = s.find('        LinearLayout tools = new LinearLayout(this);')
    end_marker = '        root.addView(more, mp);\n'
    end = s.find(end_marker, start)
    if start < 0 or end < 0:
        raise SystemExit('R8 patch failed: editor toolbar block not found')
    end += len(end_marker)

    toolbar = '''        HorizontalScrollView toolsScroll = new HorizontalScrollView(this);\n        toolsScroll.setHorizontalScrollBarEnabled(false);\n        LinearLayout tools = new LinearLayout(this);\n        tools.setOrientation(LinearLayout.HORIZONTAL);\n        tools.setPadding(dp(6), dp(5), dp(6), dp(5));\n        tools.setBackgroundColor(PANEL);\n\n        tools.addView(editorTool("Auto bordi", v -> autoDetectEdges(true)));\n        tools.addView(editorTool("Ruota ↺", v -> rotate(-90)));\n        tools.addView(editorTool("Ruota ↻", v -> rotate(90)));\n        tools.addView(editorTool("Ritaglia", v -> cropToCorners()));\n        tools.addView(editorTool("Prospettiva", v -> applyPerspective()));\n        tools.addView(editorTool("Barilotto", v -> correctDistortion(-0.08)));\n        tools.addView(editorTool("Cuscinetto", v -> correctDistortion(0.08)));\n        tools.addView(editorTool("Migliora", v -> enhanceDocument()));\n        tools.addView(editorTool("Bianco e nero", v -> blackWhiteDocument()));\n        tools.addView(editorTool("Ripristina", v -> restoreOriginal()));\n\n        toolsScroll.addView(tools);\n        root.addView(toolsScroll, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(58)));\n'''
    s = s[:start] + toolbar + s[end:]

    insert_tool = '    private LinearLayout.LayoutParams weightedTool() {'
    if insert_tool not in s:
        raise SystemExit('R8 patch failed: editor tool insertion point missing')
    editor_tool_method = '''    private Button editorTool(String text, View.OnClickListener listener) {\n        Button b = primaryTool(text, listener);\n        LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, dp(46));\n        p.setMargins(dp(4), 0, dp(4), 0);\n        b.setLayoutParams(p);\n        b.setPadding(dp(11), 0, dp(11), 0);\n        return b;\n    }\n\n'''
    s = s.replace(insert_tool, editor_tool_method + insert_tool, 1)

    func_start = s.find('    private boolean autoDetectEdges(boolean notify) {')
    func_end = s.find('    private static double maxRightAngleCosine(PointF[] p) {', func_start)
    if func_start < 0 or func_end < 0:
        raise SystemExit('R8 patch failed: auto detection function not found')

    new_auto = r'''    private boolean autoDetectEdges(boolean notify) {
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
        Mat adaptive = new Mat();
        Mat otsu = new Mat();
        Mat combined = new Mat();
        Mat kernel = new Mat();
        Mat hierarchy = new Mat();
        CLAHE clahe = null;
        try {
            Utils.bitmapToMat(currentBitmap, src);
            double scale = 1.0;
            int maxSide = Math.max(src.cols(), src.rows());
            if (maxSide > 1600) scale = 1600.0 / maxSide;
            if (scale < 1.0) Imgproc.resize(src, work, new Size(), scale, scale, Imgproc.INTER_AREA);
            else src.copyTo(work);

            Imgproc.cvtColor(work, gray, Imgproc.COLOR_RGBA2GRAY);
            clahe = Imgproc.createCLAHE(3.6, new Size(8, 8));
            clahe.apply(gray, contrast);
            Imgproc.bilateralFilter(contrast, smooth, 9, 55, 55);

            Imgproc.Canny(smooth, canny, 22, 86);
            Imgproc.adaptiveThreshold(smooth, adaptive, 255, Imgproc.ADAPTIVE_THRESH_GAUSSIAN_C,
                    Imgproc.THRESH_BINARY_INV, 41, 9);
            Imgproc.threshold(smooth, otsu, 0, 255, Imgproc.THRESH_BINARY_INV | Imgproc.THRESH_OTSU);

            Core.bitwise_or(canny, adaptive, combined);
            Core.bitwise_or(combined, otsu, combined);
            kernel = Imgproc.getStructuringElement(Imgproc.MORPH_RECT, new Size(7, 7));
            Imgproc.morphologyEx(combined, combined, Imgproc.MORPH_CLOSE, kernel);
            Imgproc.morphologyEx(combined, combined, Imgproc.MORPH_CLOSE, kernel);
            Imgproc.dilate(combined, combined, Imgproc.getStructuringElement(Imgproc.MORPH_RECT, new Size(3, 3)));

            List<MatOfPoint> contours = new ArrayList<>();
            Imgproc.findContours(combined, contours, hierarchy, Imgproc.RETR_LIST, Imgproc.CHAIN_APPROX_SIMPLE);

            double imageArea = (double) work.cols() * work.rows();
            double diagonal = Math.sqrt(work.cols() * (double) work.cols() + work.rows() * (double) work.rows());
            Point[] bestQuad = null;
            double bestQuadScore = -1e9;
            Point[] bestFallback = null;
            double bestFallbackScore = -1e9;

            for (MatOfPoint contour : contours) {
                double contourArea = Math.abs(Imgproc.contourArea(contour));
                double areaRatio = contourArea / imageArea;
                if (areaRatio < 0.025 || areaRatio > 0.998) {
                    contour.release();
                    continue;
                }

                MatOfPoint2f curve = new MatOfPoint2f(contour.toArray());
                double perimeter = Imgproc.arcLength(curve, true);
                double[] eps = {0.010, 0.014, 0.018, 0.024, 0.032, 0.045, 0.060, 0.080};

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
                            double centerDistance = Math.sqrt(
                                    (cx - work.cols() / 2.0) * (cx - work.cols() / 2.0) +
                                    (cy - work.rows() / 2.0) * (cy - work.rows() / 2.0)) / Math.max(1.0, diagonal / 2.0);
                            centerDistance = Math.min(1.0, centerDistance);
                            double score = qRatio * 7.0 + (1.0 - anglePenalty) * 2.2 + (1.0 - centerDistance) * 0.7;
                            if (qRatio >= 0.12 && qRatio <= 0.97) score += 0.6;
                            if (score > bestQuadScore) {
                                bestQuadScore = score;
                                bestQuad = pts.clone();
                            }
                        }
                        quad.release();
                    }
                    approx.release();
                }

                RotatedRect rr = Imgproc.minAreaRect(curve);
                double rectArea = Math.abs(rr.size.width * rr.size.height);
                double rectRatio = rectArea / imageArea;
                if (rectRatio >= 0.035 && rectRatio <= 0.995 && rectArea > 1.0) {
                    double fill = Math.min(1.0, contourArea / rectArea);
                    double centerDistance = Math.sqrt(
                            (rr.center.x - work.cols() / 2.0) * (rr.center.x - work.cols() / 2.0) +
                            (rr.center.y - work.rows() / 2.0) * (rr.center.y - work.rows() / 2.0)) / Math.max(1.0, diagonal / 2.0);
                    centerDistance = Math.min(1.0, centerDistance);
                    double score = rectRatio * 4.2 + fill * 1.5 + (1.0 - centerDistance) * 0.5;
                    if (rectRatio >= 0.10 && rectRatio <= 0.96) score += 0.45;
                    if (score > bestFallbackScore) {
                        Point[] rect = new Point[4];
                        rr.points(rect);
                        bestFallback = rect;
                        bestFallbackScore = score;
                    }
                }

                curve.release();
                contour.release();
            }

            Point[] selected = bestQuad != null ? bestQuad : bestFallback;
            if (selected != null) {
                PointF[] ordered = orderCorners(selected);
                float inv = (float) (1.0 / scale);
                for (PointF p : ordered) {
                    p.x = Math.max(0, Math.min(currentBitmap.getWidth() - 1, p.x * inv));
                    p.y = Math.max(0, Math.min(currentBitmap.getHeight() - 1, p.y * inv));
                }
                documentView.setCorners(ordered);
                status.setText(bestQuad != null
                        ? "Bordi del documento rilevati automaticamente. Controllali prima di applicare Prospettiva."
                        : "Documento individuato automaticamente. Controlla i quattro punti verdi prima di applicare Prospettiva.");
                if (notify) Toast.makeText(this, "Documento rilevato", Toast.LENGTH_SHORT).show();
                return true;
            }

            documentView.resetCorners();
            status.setText("Non riesco a riconoscere il foglio con sufficiente sicurezza. Sposta i quattro punti verdi sugli angoli.");
            if (notify) Toast.makeText(this, "Bordi non rilevati: usa i quattro punti verdi", Toast.LENGTH_LONG).show();
            return false;
        } catch (Exception e) {
            documentView.resetCorners();
            status.setText("Rilevamento automatico non riuscito. Usa i quattro punti verdi.");
            if (notify) Toast.makeText(this, "Rilevamento automatico non riuscito", Toast.LENGTH_SHORT).show();
            return false;
        } finally {
            if (clahe != null) clahe.clear();
            src.release(); work.release(); gray.release(); contrast.release(); smooth.release();
            canny.release(); adaptive.release(); otsu.release(); combined.release(); kernel.release(); hierarchy.release();
        }
    }

'''
    s = s[:func_start] + new_auto + s[func_end:]

    s = s.replace('Imgproc.createCLAHE(2.8, new Size(8, 8))', 'Imgproc.createCLAHE(4.2, new Size(8, 8))')
    s = s.replace('Core.addWeighted(enhancedRgb, 1.55, blur, -0.55, 0, sharp);',
                  'Core.addWeighted(enhancedRgb, 1.80, blur, -0.80, 0, sharp);')
    s = s.replace('sharp.convertTo(sharp, -1, 1.06, 3);', 'sharp.convertTo(sharp, -1, 1.10, 5);')
    s = s.replace('Testo e contrasto migliorati in modo più deciso.', 'Contrasto, illuminazione e nitidezza del documento migliorati.')

    EDITOR.write_text(s, encoding='utf-8')


patch_main()
patch_editor()
print('Android R8 patch applied successfully')
