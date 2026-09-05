from pathlib import Path

MAIN = Path('android-r3/app/src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java')
GRADLE = Path('android-r3/app/build.gradle')
s = MAIN.read_text(encoding='utf-8')


def replace_block(text, signature, replacement):
    start = text.find(signature)
    if start < 0:
        raise SystemExit(f'R32 patch failed: missing {signature}')
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
        raise SystemExit(f'R32 patch failed: unclosed {signature}')
    return text[:start] + replacement.rstrip() + '\n' + text[end:]


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
        java.util.ArrayList<JSONObject> ordered = r31SortedByDate(events, true, "startDate", "date", "createdAt");
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
s = replace_block(s, '    private void renderPanoramica() {', panoramica)

cronologia = r'''    private void renderCronologia() {
        JSONArray rows = r32ClinicalTimeline();
        boolean oldestFirst = prefs.getBoolean("r32_timeline_oldest_first", false);
        LinearLayout intro = card();
        intro.addView(sectionHeader("Cronologia clinica"));
        intro.addView(labelValue("Eventi clinici", String.valueOf(rows.length())));
        intro.addView(text("La Cronologia contiene esclusivamente dati clinici. Eventi Agenda e rilevazioni di monitoraggio, comprese le pesate, restano nelle rispettive sezioni.", 13, MUTED, false));
        Button order = button(oldestFirst ? "Ordine: meno recenti prima" : "Ordine: più recenti prima");
        order.setOnClickListener(v -> { prefs.edit().putBoolean("r32_timeline_oldest_first", !oldestFirst).apply(); renderSection("Cronologia"); });
        intro.addView(order, matchWrapTop(8));
        content.addView(intro, matchWrapBottom(14));
        java.util.ArrayList<JSONObject> ordered = r31SortedByDate(rows, oldestFirst, "date");
        if (ordered.isEmpty()) {
            LinearLayout empty = card();
            empty.addView(text("Nessun dato clinico datato presente.", 13, MUTED, false));
            content.addView(empty, matchWrapBottom(14));
            return;
        }
        int max = Math.min(ordered.size(), 150);
        for (int i = 0; i < max; i++) {
            JSONObject row = ordered.get(i);
            LinearLayout c = card();
            c.addView(text(row.optString("kind", "Dato clinico"), 12, GREEN_DARK, true));
            c.addView(text(row.optString("title", "Dato clinico"), 15, TEXT, true));
            r31AddIf(c, "Data", row.optString("date", ""));
            content.addView(c, matchWrapBottom(8));
        }
    }'''
s = replace_block(s, '    private void renderCronologia() {', cronologia)

esenzioni = r'''    private void renderEsenzioni() {
        JSONArray rows = R27ExactWindows.exemptions(prefs);
        boolean extended = prefs.getBoolean("r31_exemptions_extended", "extended".equalsIgnoreCase(R27ExactWindows.profilePreferences(prefs).optString("exemptionView", "compact")));
        boolean oldestFirst = prefs.getBoolean("r32_exemptions_oldest_first", false);
        LinearLayout intro = card();
        intro.addView(sectionHeader("Esenzioni"));
        intro.addView(labelValue("Esenzioni registrate", String.valueOf(rows.length())));
        Button mode = button(extended ? "Passa alla vista compatta" : "Passa alla vista estesa");
        mode.setOnClickListener(v -> { prefs.edit().putBoolean("r31_exemptions_extended", !extended).apply(); renderSection("Esenzioni"); });
        intro.addView(mode, matchWrapTop(8));
        Button order = button(oldestFirst ? "Ordine: scadenze meno recenti prima" : "Ordine: scadenze più recenti prima");
        order.setOnClickListener(v -> { prefs.edit().putBoolean("r32_exemptions_oldest_first", !oldestFirst).apply(); renderSection("Esenzioni"); });
        intro.addView(order, matchWrapTop(8));
        content.addView(intro, matchWrapBottom(14));
        java.util.ArrayList<JSONObject> ordered = r31SortedByDate(rows, oldestFirst, "expiry", "validTo", "validFrom", "createdAt");
        for (JSONObject row : ordered) {
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
        if (ordered.isEmpty()) { LinearLayout e = card(); e.addView(text("Nessuna esenzione registrata.", 13, MUTED, false)); content.addView(e, matchWrapBottom(14)); }
    }'''
s = replace_block(s, '    private void renderEsenzioni() {', esenzioni)

diagnosi = r'''    private void renderDiagnosi() {
        JSONArray rows = R27ExactWindows.diagnoses(prefs);
        boolean oldestFirst = prefs.getBoolean("r32_diagnoses_oldest_first", false);
        LinearLayout intro = card();
        intro.addView(sectionHeader("Diagnosi"));
        intro.addView(labelValue("Diagnosi / condizioni", String.valueOf(rows.length())));
        Button order = button(oldestFirst ? "Ordine: meno recenti prima" : "Ordine: più recenti prima");
        order.setOnClickListener(v -> { prefs.edit().putBoolean("r32_diagnoses_oldest_first", !oldestFirst).apply(); renderSection("Diagnosi"); });
        intro.addView(order, matchWrapTop(8));
        content.addView(intro, matchWrapBottom(14));
        java.util.ArrayList<JSONObject> ordered = r31SortedByDate(rows, oldestFirst, "date", "diagnosisDate", "createdAt");
        if (ordered.isEmpty()) { LinearLayout e = card(); e.addView(text("Nessuna diagnosi o condizione registrata.", 13, MUTED, false)); content.addView(e, matchWrapBottom(14)); return; }
        for (JSONObject row : ordered) {
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
s = replace_block(s, '    private void renderDiagnosi() {', diagnosi)

terapie = r'''    private void renderTerapie() {
        JSONArray rows = R27ExactWindows.therapies(prefs);
        String sort = prefs.getString("r32_therapy_sort", R27ExactWindows.profilePreferences(prefs).optString("therapySort", "time-asc"));
        LinearLayout intro = card();
        intro.addView(sectionHeader("Terapie"));
        intro.addView(labelValue("Terapie registrate", String.valueOf(rows.length())));
        Button sortButton = button("Ordina: " + r32TherapySortLabel(sort));
        sortButton.setOnClickListener(v -> r32ShowTherapySort(sort));
        intro.addView(sortButton, matchWrapTop(8));
        Button add = button("Aggiungi terapia"); add.setOnClickListener(v -> r31EditTherapy(null)); intro.addView(add, matchWrapTop(8));
        content.addView(intro, matchWrapBottom(14));
        java.util.ArrayList<JSONObject> ordered = r32SortedTherapies(rows, sort);
        if (ordered.isEmpty()) { LinearLayout e = card(); e.addView(text("Nessuna terapia registrata.", 13, MUTED, false)); content.addView(e, matchWrapBottom(14)); return; }
        for (JSONObject row : ordered) {
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
s = replace_block(s, '    private void renderTerapie() {', terapie)

medici = r'''    private void renderMedici() {
        JSONArray rows = R27ExactWindows.doctors(prefs);
        boolean asc = prefs.getBoolean("r32_doctors_name_asc", true);
        LinearLayout intro = card();
        intro.addView(sectionHeader("Medici e specialisti"));
        intro.addView(labelValue("Contatti registrati", String.valueOf(rows.length())));
        Button order = button(asc ? "Ordine: nome A-Z" : "Ordine: nome Z-A");
        order.setOnClickListener(v -> { prefs.edit().putBoolean("r32_doctors_name_asc", !asc).apply(); renderSection("Medici e specialisti"); });
        intro.addView(order, matchWrapTop(8));
        Button add = button("Aggiungi medico"); add.setOnClickListener(v -> r31EditDoctor(null)); intro.addView(add, matchWrapTop(8));
        content.addView(intro, matchWrapBottom(14));
        java.util.ArrayList<JSONObject> ordered = r32SortedByText(rows, asc, "name", "displayName");
        if (ordered.isEmpty()) { LinearLayout e = card(); e.addView(text("Nessun medico o specialista registrato.", 13, MUTED, false)); content.addView(e, matchWrapBottom(14)); return; }
        for (JSONObject row : ordered) {
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
s = replace_block(s, '    private void renderMedici() {', medici)

agenda = r'''    private void renderAgenda() {
        JSONArray rows = R27ExactWindows.calendarEvents(prefs);
        boolean nearestFirst = prefs.getBoolean("r32_agenda_nearest_first", true);
        LinearLayout intro = card();
        intro.addView(sectionHeader("Agenda"));
        intro.addView(labelValue("Eventi registrati", String.valueOf(rows.length())));
        Button order = button(nearestFirst ? "Ordine: scadenze più vicine prima" : "Ordine: scadenze più lontane prima");
        order.setOnClickListener(v -> { prefs.edit().putBoolean("r32_agenda_nearest_first", !nearestFirst).apply(); renderSection("Agenda"); });
        intro.addView(order, matchWrapTop(8));
        Button add = button("Nuovo appuntamento"); add.setOnClickListener(v -> r31EditAgendaEvent(null)); intro.addView(add, matchWrapTop(8));
        Button sync = button("Sincronizza Agenda"); sync.setOnClickListener(v -> R12CloudManager.syncInteractiveR31(this, prefs)); intro.addView(sync, matchWrapTop(8));
        content.addView(intro, matchWrapBottom(14));
        java.util.ArrayList<JSONObject> ordered = r31SortedByDate(rows, nearestFirst, "startDate", "date", "createdAt");
        if (ordered.isEmpty()) { LinearLayout e=card();e.addView(text("Nessun evento registrato.",13,MUTED,false));content.addView(e,matchWrapBottom(14));return; }
        for (JSONObject row : ordered) {
            LinearLayout c=card(); c.addView(text(r31First(row,"title","name","category"),16,TEXT,true));
            r31AddIf(c,"Tipo",r31CategoryItalian(r31First(row,"category","type")));
            r31AddIf(c,"Data",r31First(row,"startDate","date"));
            String time=r31First(row,"startTime","time"); c.addView(labelValue("Ora",row.optBoolean("allDay",false)||time.isEmpty()?"Tutto il giorno":time));
            if(row.has("durationMinutes"))c.addView(labelValue("Durata",row.optInt("durationMinutes",60)+" minuti"));
            r31AddIf(c,"Stato",r31StatusItalian(row.optString("status","")));
            r31AddIf(c,"Luogo / struttura",row.optString("location","")); r31AddIf(c,"Note",row.optString("notes",""));
            Button edit=button("Modifica appuntamento");edit.setOnClickListener(v->r31EditAgendaEvent(row));c.addView(edit,matchWrapTop(8));
            content.addView(c,matchWrapBottom(10));
        }
    }'''
s = replace_block(s, '    private void renderAgenda() {', agenda)

monitor_detail = r'''    private void r31RenderMonitorDetail(String type,String label){
        content.removeAllViews();viewTitle.setText(label);viewSubtitle.setText("Storico, grafici e inserimento manuale delle rilevazioni.");
        boolean oldestFirst=prefs.getBoolean("r32_monitor_"+type+"_oldest_first",false);
        LinearLayout top=card();
        Button back=compactButton("← Torna a Monitoraggio");back.setOnClickListener(v->renderSection("Monitoraggio"));top.addView(back);
        Button order=button(oldestFirst?"Ordine: meno recenti prima":"Ordine: più recenti prima");
        order.setOnClickListener(v->{prefs.edit().putBoolean("r32_monitor_"+type+"_oldest_first",!oldestFirst).apply();r31RenderMonitorDetail(type,label);});top.addView(order,matchWrapTop(8));
        Button add=button("Aggiungi rilevazione");add.setOnClickListener(v->{if("body".equals(type))r31ChooseBodyMeasurement();else r31EditMeasurement(type,null);});top.addView(add,matchWrapTop(8));content.addView(top,matchWrapBottom(14));
        JSONArray rows="body".equals(type)?r31BodyMeasurements():R27ExactWindows.measurementsOf(prefs,type);
        r32AddMonitorGraphs(type,label,rows);
        java.util.ArrayList<JSONObject> ordered=r31SortedByDate(rows,oldestFirst,"date","createdAt","updatedAt");
        if(ordered.isEmpty()){LinearLayout e=card();e.addView(text("Nessuna rilevazione registrata.",13,MUTED,false));content.addView(e,matchWrapBottom(14));return;}
        if("weight".equals(type)){
            LinearLayout history=card();history.addView(sectionHeader("Storico pesate"));
            for(JSONObject row:ordered){
                LinearLayout line=new LinearLayout(this);line.setOrientation(LinearLayout.HORIZONTAL);line.setGravity(Gravity.CENTER_VERTICAL);line.setPadding(0,dp(3),0,dp(3));
                String date=r31First(row,"date","createdAt");String time=row.optString("time","");String when=date+(time.isEmpty()?"":"  "+time);
                TextView left=text(when.isEmpty()?"Data non indicata":when,13,TEXT,false);line.addView(left,new LinearLayout.LayoutParams(0,ViewGroup.LayoutParams.WRAP_CONTENT,1f));
                String value=row.optString("value","")+(row.optString("unit","").isEmpty()?"":" "+row.optString("unit",""));TextView val=text(value,14,TEXT,true);val.setGravity(Gravity.END);line.addView(val,new LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT,ViewGroup.LayoutParams.WRAP_CONTENT));
                Button edit=compactButton("Modifica");edit.setOnClickListener(v->r31EditMeasurement("weight",row));LinearLayout.LayoutParams ep=new LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT,dp(40));ep.setMargins(dp(7),0,0,0);line.addView(edit,ep);
                history.addView(line);
            }
            content.addView(history,matchWrapBottom(12));
            return;
        }
        for(JSONObject row:ordered){LinearLayout c=card();String rowLabel="body".equals(type)?r31BodyLabel(row.optString("type","")):label;c.addView(text(rowLabel,15,TEXT,true));r31AddIf(c,"Data",r31First(row,"date","createdAt"));r31AddIf(c,"Ora",row.optString("time",""));if("blood_pressure".equals(type)){r31AddIf(c,"Sistolica",row.optString("systolic",""));r31AddIf(c,"Diastolica",row.optString("diastolic",""));r31AddIf(c,"Frequenza cardiaca",row.optString("heartRate",""));}else{r31AddIf(c,"Valore",row.optString("value","")+(row.optString("unit","").isEmpty()?"":" "+row.optString("unit","")));}r31AddIf(c,"Contesto",row.optString("context",""));r31AddIf(c,"Dispositivo",row.optString("device",""));r31AddIf(c,"Note",row.optString("notes",""));Button edit=compactButton("Modifica");String actual=row.optString("type",type);edit.setOnClickListener(v->r31EditMeasurement(actual,row));c.addView(edit,matchWrapTop(7));content.addView(c,matchWrapBottom(9));}
    }'''
s = replace_block(s, '    private void r31RenderMonitorDetail(String type,String label){', monitor_detail)

insert = '    private void renderBackup() {'
if insert not in s:
    raise SystemExit('R32 patch failed: renderBackup insertion point missing')
helpers = r'''    private JSONArray r32ClinicalTimeline(){
        JSONArray all=R27ExactWindows.timeline(prefs),out=new JSONArray();
        for(int i=0;i<all.length();i++){
            JSONObject row=all.optJSONObject(i);if(row==null)continue;
            String kind=row.optString("kind","").trim();
            if("Agenda".equalsIgnoreCase(kind)||"Rilevazione".equalsIgnoreCase(kind))continue;
            out.put(row);
        }
        return out;
    }

    private java.util.ArrayList<JSONObject> r32SortedByText(JSONArray source,boolean asc,String...keys){
        java.util.ArrayList<JSONObject> list=new java.util.ArrayList<>();
        if(source!=null)for(int i=0;i<source.length();i++)if(source.optJSONObject(i)!=null)list.add(source.optJSONObject(i));
        list.sort((a,b)->{String aa=r31First(a,keys).toLowerCase(Locale.ROOT),bb=r31First(b,keys).toLowerCase(Locale.ROOT);int cmp=aa.compareTo(bb);return asc?cmp:-cmp;});
        return list;
    }

    private String r32TherapySortLabel(String sort){
        if("time-desc".equals(sort))return"orario decrescente";
        if("name-asc".equals(sort))return"farmaco A-Z";
        if("name-desc".equals(sort))return"farmaco Z-A";
        return"orario crescente";
    }

    private void r32ShowTherapySort(String current){
        String[] labels={"Orario crescente","Orario decrescente","Farmaco A-Z","Farmaco Z-A"};
        String[] values={"time-asc","time-desc","name-asc","name-desc"};
        int checked=0;for(int i=0;i<values.length;i++)if(values[i].equals(current))checked=i;
        new AlertDialog.Builder(this).setTitle("Ordina terapie").setSingleChoiceItems(labels,checked,(dialog,which)->{
            prefs.edit().putString("r32_therapy_sort",values[which]).apply();dialog.dismiss();renderSection("Terapie");
        }).setNegativeButton("Chiudi",null).show();
    }

    private int r32TherapyMinutes(JSONObject row){
        String raw=r31First(row,"time","times");if(raw.isEmpty())return 24*60+1;
        java.util.regex.Matcher m=java.util.regex.Pattern.compile("(\\d{1,2})\\s*[:.]\\s*(\\d{2})").matcher(raw);
        if(m.find()){try{return Integer.parseInt(m.group(1))*60+Integer.parseInt(m.group(2));}catch(Exception ignored){}}
        m=java.util.regex.Pattern.compile("\\b(\\d{1,2})\\b").matcher(raw);
        if(m.find()){try{return Integer.parseInt(m.group(1))*60;}catch(Exception ignored){}}
        return 24*60+1;
    }

    private java.util.ArrayList<JSONObject> r32SortedTherapies(JSONArray source,String sort){
        java.util.ArrayList<JSONObject> list=new java.util.ArrayList<>();if(source!=null)for(int i=0;i<source.length();i++)if(source.optJSONObject(i)!=null)list.add(source.optJSONObject(i));
        list.sort((a,b)->{
            int cmp;
            if(sort.startsWith("name")){cmp=r31First(a,"medication","farmaco","name").compareToIgnoreCase(r31First(b,"medication","farmaco","name"));}
            else{cmp=Integer.compare(r32TherapyMinutes(a),r32TherapyMinutes(b));if(cmp==0)cmp=r31First(a,"medication","farmaco","name").compareToIgnoreCase(r31First(b,"medication","farmaco","name"));}
            return sort.endsWith("desc")?-cmp:cmp;
        });return list;
    }

    private JSONArray r32Array(java.util.ArrayList<JSONObject> list){JSONArray out=new JSONArray();for(JSONObject row:list)out.put(row);return out;}

    private void r32AddMonitorGraphs(String type,String label,JSONArray rows){
        if(rows==null||rows.length()==0)return;
        if("blood_pressure".equals(type)){
            JSONArray chronological=r32Array(r31SortedByDate(rows,true,"date","createdAt","updatedAt"));
            r27Chart("Pressione sistolica",chronological,"systolic");r27Chart("Pressione diastolica",chronological,"diastolic");r27Chart("Frequenza cardiaca",chronological,"heartRate");return;
        }
        if("body".equals(type)){
            String[] types={"height","neck","chest","waist","abdomen","hips","arm_right","arm_left","thigh_right","thigh_left","calf_right","calf_left","wrist_right","wrist_left","ankle_right","ankle_left"};
            for(String bodyType:types){JSONArray subset=new JSONArray();for(int i=0;i<rows.length();i++){JSONObject r=rows.optJSONObject(i);if(r!=null&&bodyType.equals(r.optString("type","")))subset.put(r);}if(subset.length()>0)r27Chart(r31BodyLabel(bodyType),r32Array(r31SortedByDate(subset,true,"date","createdAt","updatedAt")),"value");}
            return;
        }
        JSONArray chronological=r32Array(r31SortedByDate(rows,true,"date","createdAt","updatedAt"));
        r27Chart("Andamento "+label,chronological,"value");
    }

'''
s = s.replace(insert, helpers + insert, 1)

s = s.replace('Android R31 TEST COMPLETO', 'Android R32 TEST COMPLETO')
s = s.replace('Aiuto R31', 'Aiuto R32')
s = s.replace('R31: sezione mobile completa collegata al Dossier Windows', 'R32: sezione mobile completa collegata al Dossier Windows')
MAIN.write_text(s, encoding='utf-8')

g = GRADLE.read_text(encoding='utf-8')
g = g.replace('versionCode 31', 'versionCode 32')
g = g.replace("versionName '1.0.0-android-r31-mobile-parity-test'", "versionName '1.0.0-android-r32-ordering-monitor-test'")
GRADLE.write_text(g, encoding='utf-8')
print('R32 ordering, clinical timeline and monitoring graphs patch applied')
