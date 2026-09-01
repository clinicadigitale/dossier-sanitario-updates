from pathlib import Path
import runpy

BASE = Path('android-r3/app/src/main/java/it/dossiersanitario/clinicadigitale/beta')
MAIN = BASE / 'R6MainActivity.java'


def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit(f'R10 patch failed: missing {label}')
    return text.replace(old, new, 1)


def patch_main():
    s = MAIN.read_text(encoding='utf-8')

    s = replace_once(
        s,
        'import java.util.Locale;\nimport java.util.zip.ZipEntry;',
        'import java.util.Locale;\nimport java.util.concurrent.ExecutorService;\nimport java.util.concurrent.Executors;\nimport java.util.zip.ZipEntry;',
        'executor imports'
    )

    s = replace_once(
        s,
        '    private Uri pendingRestoreUri = null;\n',
        '    private Uri pendingRestoreUri = null;\n'
        '    private LinearLayout agendaList = null;\n'
        '    private final ExecutorService dataExecutor = Executors.newSingleThreadExecutor();\n',
        'agenda performance state'
    )

    s = replace_once(
        s,
        '    @Override protected void onSaveInstanceState(Bundle outState) {\n'
        '        outState.putString("current_section", currentSection);\n'
        '        super.onSaveInstanceState(outState);\n'
        '    }\n',
        '    @Override protected void onSaveInstanceState(Bundle outState) {\n'
        '        outState.putString("current_section", currentSection);\n'
        '        super.onSaveInstanceState(outState);\n'
        '    }\n\n'
        '    @Override protected void onDestroy() {\n'
        '        dataExecutor.shutdown();\n'
        '        super.onDestroy();\n'
        '    }\n',
        'executor lifecycle'
    )

    s = replace_once(
        s,
        '        photoList = null;\n        testField = null;',
        '        photoList = null;\n        agendaList = null;\n        testField = null;',
        'agenda view reset'
    )

    s = replace_once(
        s,
        '    private void upsertClinicalEvent(JSONObject object) throws Exception {',
        '    private synchronized void upsertClinicalEvent(JSONObject object) throws Exception {',
        'clinical serialized writes'
    )

    start = s.find('    private void renderAgenda() {')
    end = s.find('    private void showAgendaDialog(JSONObject existing) {', start)
    if start < 0 or end < 0:
        raise SystemExit('R10 patch failed: agenda render block not found')

    agenda_render = r'''    private void renderAgenda() {
        LinearLayout intro = card();
        intro.addView(sectionHeader("Agenda"));
        intro.addView(text("Visite, esami e appuntamenti sanitari del profilo. Gli eventi salvati qui vengono riportati anche nella Cronologia clinica.", 13, MUTED, false));
        Button add = button("Aggiungi appuntamento");
        add.setOnClickListener(v -> showAgendaDialog(null));
        intro.addView(add, matchWrapTop(10));
        content.addView(intro, matchWrapBottom(14));

        agendaList = new LinearLayout(this);
        agendaList.setOrientation(LinearLayout.VERTICAL);
        content.addView(agendaList, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        JSONArray items = readArray(PREF_AGENDA);
        if (items.length() == 0) {
            addAgendaEmptyState();
            return;
        }
        for (int i = 0; i < items.length(); i++) {
            JSONObject item = items.optJSONObject(i);
            if (item != null) agendaList.addView(buildAgendaCard(item), matchWrapBottom(10));
        }
    }

    private LinearLayout buildAgendaCard(JSONObject item) {
        long id = item.optLong("id", 0L);
        LinearLayout c = card();
        c.setTag(Long.valueOf(id));
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
        return c;
    }

    private void addAgendaEmptyState() {
        if (agendaList == null || agendaList.getChildCount() > 0) return;
        LinearLayout empty = card();
        empty.setTag("agenda_empty");
        empty.addView(text("Nessun appuntamento sanitario registrato.", 14, MUTED, false));
        agendaList.addView(empty, matchWrapBottom(14));
    }

    private void refreshAgendaCard(JSONObject item) {
        if (agendaList == null) return;
        long id = item.optLong("id", 0L);
        for (int i = agendaList.getChildCount() - 1; i >= 0; i--) {
            View child = agendaList.getChildAt(i);
            Object tag = child.getTag();
            if ("agenda_empty".equals(tag) || (tag instanceof Long && ((Long) tag).longValue() == id)) {
                agendaList.removeViewAt(i);
            }
        }
        agendaList.addView(buildAgendaCard(item), 0, matchWrapBottom(10));
    }

    private void removeAgendaCard(long id) {
        if (agendaList == null) return;
        for (int i = agendaList.getChildCount() - 1; i >= 0; i--) {
            View child = agendaList.getChildAt(i);
            Object tag = child.getTag();
            if (tag instanceof Long && ((Long) tag).longValue() == id) agendaList.removeViewAt(i);
        }
        addAgendaEmptyState();
    }

    private void mirrorAgendaToClinicalAsync(JSONObject object) {
        final String snapshot = object.toString();
        dataExecutor.execute(() -> {
            try {
                JSONObject clinical = new JSONObject(snapshot);
                clinical.put("source", "agenda");
                upsertClinicalEvent(clinical);
            } catch (Exception ignored) {
            }
        });
    }

    private void removeAgendaClinicalMirrorAsync(long id) {
        dataExecutor.execute(() -> {
            synchronized (R6MainActivity.this) {
                JSONArray clinical = readArray(PREF_CLINICAL_EVENTS);
                for (int i = clinical.length() - 1; i >= 0; i--) {
                    JSONObject obj = clinical.optJSONObject(i);
                    if (obj != null && obj.optLong("id", -1L) == id && "agenda".equals(obj.optString("source", ""))) clinical.remove(i);
                }
                saveArray(PREF_CLINICAL_EVENTS, clinical);
            }
        });
    }

'''
    s = s[:start] + agenda_render + s[end:]

    s = replace_once(
        s,
        '                        upsertRecord(PREF_AGENDA, obj);\n'
        '                        JSONObject clinical = new JSONObject(obj.toString());\n'
        '                        clinical.put("source", "agenda");\n'
        '                        upsertClinicalEvent(clinical);\n'
        '                        renderSection("Agenda");',
        '                        upsertRecord(PREF_AGENDA, obj);\n'
        '                        refreshAgendaCard(obj);\n'
        '                        mirrorAgendaToClinicalAsync(obj);\n'
        '                        Toast.makeText(this, "Appuntamento salvato", Toast.LENGTH_SHORT).show();',
        'quick agenda save'
    )

    old_delete = '''                    saveArray(PREF_AGENDA, agenda);\n                    JSONArray clinical = readArray(PREF_CLINICAL_EVENTS);\n                    for (int i = clinical.length() - 1; i >= 0; i--) {\n                        JSONObject obj = clinical.optJSONObject(i);\n                        if (obj != null && obj.optLong("id", -1L) == id && "agenda".equals(obj.optString("source", ""))) clinical.remove(i);\n                    }\n                    saveArray(PREF_CLINICAL_EVENTS, clinical);\n                    renderSection("Agenda");'''
    new_delete = '''                    saveArray(PREF_AGENDA, agenda);\n                    removeAgendaCard(id);\n                    removeAgendaClinicalMirrorAsync(id);\n                    Toast.makeText(this, "Appuntamento eliminato", Toast.LENGTH_SHORT).show();'''
    s = replace_once(s, old_delete, new_delete, 'quick agenda delete')

    visible = {
        'Android R9 TEST': 'Android R10 TEST',
        'Aiuto R9': 'Aiuto R10',
        'R9: struttura presente': 'R10: struttura presente',
        'R9 mantiene lo stesso pacchetto Android': 'R10 mantiene lo stesso pacchetto Android',
        'Installala sopra la R8': 'Installala sopra la R9',
        'Importazione file non ancora attiva nella R9': 'Importazione file non ancora attiva nella R10'
    }
    for old, new in visible.items():
        s = s.replace(old, new)

    MAIN.write_text(s, encoding='utf-8')


patch_main()
print('Android R10 performance patch applied successfully')
runpy.run_path('android-r3/r11_patch.py', run_name='__main__')
