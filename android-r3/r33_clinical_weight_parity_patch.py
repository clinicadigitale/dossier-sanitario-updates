from pathlib import Path

MAIN = Path('android-r3/app/src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java')
GRADLE = Path('android-r3/app/build.gradle')
s = MAIN.read_text(encoding='utf-8')


def replace_block(text, signature, replacement):
    start = text.find(signature)
    if start < 0:
        raise SystemExit(f'R33 patch failed: missing {signature}')
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
        raise SystemExit(f'R33 patch failed: unclosed {signature}')
    return text[:start] + replacement.rstrip() + '\n' + text[end:]


# Imports used only by the R33 fixes.
if 'import android.content.res.Configuration;' not in s:
    s = s.replace('import android.content.pm.PackageManager;\n', 'import android.content.pm.PackageManager;\nimport android.content.res.Configuration;\n', 1)
if 'import android.widget.ProgressBar;' not in s:
    s = s.replace('import android.widget.LinearLayout;\n', 'import android.widget.LinearLayout;\nimport android.widget.ProgressBar;\n', 1)

# Internal Monitoraggio navigation must have priority over the global history stack.
field_marker = '    private long lastPanoramicaBackMs = 0L;'
if field_marker not in s:
    raise SystemExit('R33 patch failed: navigation field marker missing')
s = s.replace(field_marker, field_marker + '\n    private boolean r33MonitorDetailOpen = false;', 1)

back = r'''    @Override public void onBackPressed() {
        if (r33MonitorDetailOpen) {
            r33MonitorDetailOpen = false;
            renderSection("Monitoraggio");
            return;
        }
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
    }'''
s = replace_block(s, '    @Override public void onBackPressed() {', back)

# Landscape only: keep graph content inside the left/right system-bar safe area.
old_insets = '''        root.setOnApplyWindowInsetsListener((v, insets) -> {\n            int top = insets.getSystemWindowInsetTop();\n            int bottom = insets.getSystemWindowInsetBottom();\n            v.setPadding(0, top, 0, bottom);\n            return insets;\n        });'''
new_insets = '''        root.setOnApplyWindowInsetsListener((v, insets) -> {\n            int top = insets.getSystemWindowInsetTop();\n            int bottom = insets.getSystemWindowInsetBottom();\n            boolean landscape = getResources().getConfiguration().orientation == Configuration.ORIENTATION_LANDSCAPE;\n            int left = landscape ? insets.getSystemWindowInsetLeft() : 0;\n            int right = landscape ? insets.getSystemWindowInsetRight() : 0;\n            v.setPadding(left, top, right, bottom);\n            return insets;\n        });'''
if old_insets not in s:
    raise SystemExit('R33 patch failed: window insets block missing')
s = s.replace(old_insets, new_insets, 1)

# Any top-level navigation closes the internal Monitoraggio child page.
section_sig = '    private void renderSection(String section) {'
section_start = s.find(section_sig)
if section_start < 0:
    raise SystemExit('R33 patch failed: renderSection missing')
needle = '        currentSection = section;\n        content.removeAllViews();'
if needle not in s[section_start:]:
    raise SystemExit('R33 patch failed: renderSection body marker missing')
s = s[:section_start] + s[section_start:].replace(needle, '        currentSection = section;\n        r33MonitorDetailOpen = false;\n        content.removeAllViews();', 1)

cronologia = r'''    private void renderCronologia() {
        JSONArray rows = r33ClinicalTimelineDocuments();
        boolean oldestFirst = prefs.getBoolean("r32_timeline_oldest_first", false);
        LinearLayout intro = card();
        intro.addView(sectionHeader("Cronologia clinica"));
        intro.addView(labelValue("Referti, visite ed esami", String.valueOf(rows.length())));
        intro.addView(text("La Cronologia contiene soltanto referti, visite ed esami. Terapie, prenotazioni, Agenda e rilevazioni di monitoraggio restano nelle rispettive sezioni.", 13, MUTED, false));
        Button order = button(oldestFirst ? "Ordine: meno recenti prima" : "Ordine: più recenti prima");
        order.setOnClickListener(v -> { prefs.edit().putBoolean("r32_timeline_oldest_first", !oldestFirst).apply(); renderSection("Cronologia"); });
        intro.addView(order, matchWrapTop(8));
        content.addView(intro, matchWrapBottom(14));

        java.util.ArrayList<JSONObject> ordered = r31SortedByDate(rows, oldestFirst, "clinicalDate", "issueDate", "createdAt", "updatedAt");
        if (ordered.isEmpty()) {
            LinearLayout empty = card();
            empty.addView(text("Nessun referto, visita o esame datato presente.", 13, MUTED, false));
            content.addView(empty, matchWrapBottom(14));
            return;
        }
        for (JSONObject doc : ordered) {
            LinearLayout c = card();
            c.addView(text(R27ExactWindows.label(doc, "Documento clinico"), 15, TEXT, true));
            r31AddIf(c, "Data", r31First(doc, "clinicalDate", "issueDate", "createdAt", "updatedAt"));
            r31AddIf(c, "Tipologia", r31First(doc, "documentKind", "category", "type"));
            r31AddIf(c, "Specializzazione", r31First(doc, "specialization", "specialty"));
            r31AddIf(c, "Struttura", r31First(doc, "facility", "structure"));
            Button open = compactButton("Apri referto");
            open.setOnClickListener(v -> R27ExactWindows.openDocument(this, doc));
            c.addView(open, matchWrapTop(7));
            content.addView(c, matchWrapBottom(8));
        }
    }'''
s = replace_block(s, '    private void renderCronologia() {', cronologia)

monitor_detail = r'''    private void r31RenderMonitorDetail(String type,String label){
        if("weight".equals(type)) { r33RenderWeightDetail(); return; }
        r33MonitorDetailOpen = true;
        content.removeAllViews();
        viewTitle.setText(label);
        viewSubtitle.setText("Storico, grafici e inserimento manuale delle rilevazioni.");
        boolean oldestFirst=prefs.getBoolean("r32_monitor_"+type+"_oldest_first",false);
        LinearLayout top=card();
        Button back=compactButton("← Torna a Monitoraggio");
        back.setOnClickListener(v->{r33MonitorDetailOpen=false;renderSection("Monitoraggio");});
        top.addView(back);
        Button order=button(oldestFirst?"Ordine: meno recenti prima":"Ordine: più recenti prima");
        order.setOnClickListener(v->{prefs.edit().putBoolean("r32_monitor_"+type+"_oldest_first",!oldestFirst).apply();r31RenderMonitorDetail(type,label);});
        top.addView(order,matchWrapTop(8));
        Button add=button("Aggiungi rilevazione");
        add.setOnClickListener(v->{if("body".equals(type))r31ChooseBodyMeasurement();else r31EditMeasurement(type,null);});
        top.addView(add,matchWrapTop(8));
        content.addView(top,matchWrapBottom(14));

        JSONArray rows="body".equals(type)?r31BodyMeasurements():R27ExactWindows.measurementsOf(prefs,type);
        r32AddMonitorGraphs(type,label,rows);
        java.util.ArrayList<JSONObject> ordered=r31SortedByDate(rows,oldestFirst,"date","createdAt","updatedAt");
        if(ordered.isEmpty()){
            LinearLayout e=card();e.addView(text("Nessuna rilevazione registrata.",13,MUTED,false));content.addView(e,matchWrapBottom(14));return;
        }
        for(JSONObject row:ordered){
            LinearLayout c=card();
            String rowLabel="body".equals(type)?r31BodyLabel(row.optString("type","")):label;
            c.addView(text(rowLabel,15,TEXT,true));
            r31AddIf(c,"Data",r31First(row,"date","createdAt"));
            r31AddIf(c,"Ora",row.optString("time",""));
            if("blood_pressure".equals(type)){
                r31AddIf(c,"Sistolica",row.optString("systolic",""));
                r31AddIf(c,"Diastolica",row.optString("diastolic",""));
                r31AddIf(c,"Frequenza cardiaca",row.optString("heartRate",""));
            }else{
                r31AddIf(c,"Valore",row.optString("value","")+(row.optString("unit","").isEmpty()?"":" "+row.optString("unit","")));
            }
            r31AddIf(c,"Contesto",row.optString("context",""));
            r31AddIf(c,"Dispositivo",row.optString("device",""));
            r31AddIf(c,"Note",row.optString("notes",""));
            Button edit=compactButton("Modifica");String actual=row.optString("type",type);
            edit.setOnClickListener(v->r31EditMeasurement(actual,row));c.addView(edit,matchWrapTop(7));
            content.addView(c,matchWrapBottom(9));
        }
    }'''
s = replace_block(s, '    private void r31RenderMonitorDetail(String type,String label){', monitor_detail)

pressure_graphs = r'''    private void r32AddMonitorGraphs(String type,String label,JSONArray rows){
        if(rows==null||rows.length()==0)return;
        if("blood_pressure".equals(type)){
            LinearLayout c=card();
            c.addView(sectionHeader("Pressione arteriosa"));
            c.addView(text("Sistolica e diastolica nello stesso grafico, come nella versione Windows.",13,MUTED,false));
            R33PressureChartView chart=new R33PressureChartView(this,rows,R27ExactWindows.activeProfileColor(prefs,GREEN));
            if(chart.hasData())c.addView(chart,new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,dp(255)));
            content.addView(c,matchWrapBottom(14));
            r27Chart("Frequenza cardiaca",r32Array(r31SortedByDate(rows,true,"date","createdAt","updatedAt")),"heartRate");
            return;
        }
        if("body".equals(type)){
            String[] bodyTypes={"waist","chest","hips","arm","thigh","neck"};
            for(String bodyType:bodyTypes){
                JSONArray one=new JSONArray();
                for(int i=0;i<rows.length();i++){
                    JSONObject row=rows.optJSONObject(i);
                    if(row!=null&&bodyType.equalsIgnoreCase(row.optString("type","")))one.put(row);
                }
                if(one.length()>0)r27Chart(r31BodyLabel(bodyType),r32Array(r31SortedByDate(one,true,"date","createdAt","updatedAt")),"value");
            }
            return;
        }
        JSONArray chronological=r32Array(r31SortedByDate(rows,true,"date","createdAt","updatedAt"));
        r27Chart("Andamento "+label,chronological,"value");
        if("spo2".equals(type))r27Chart("Frequenza cardiaca",chronological,"heartRate");
    }'''
s = replace_block(s, '    private void r32AddMonitorGraphs(String type,String label,JSONArray rows){', pressure_graphs)

selector = r'''    private void r31SelectClinicalValue(boolean graph) {
        java.util.ArrayList<String> labels=new java.util.ArrayList<>();
        java.util.ArrayList<String> codes=new java.util.ArrayList<>();
        r31AddClinicalChoice(labels,codes,"Peso","m|weight|value|Peso");
        r31AddClinicalChoice(labels,codes,"Saturazione ossigeno","m|spo2|value|Saturazione ossigeno");
        r31AddClinicalChoice(labels,codes,"Glicemia domestica","m|glucose|value|Glicemia domestica");
        r31AddClinicalChoice(labels,codes,"Frequenza cardiaca","m|heart_rate|value|Frequenza cardiaca");
        if(graph){
            r31AddClinicalChoice(labels,codes,"Pressione arteriosa","p|blood_pressure|both|Pressione arteriosa");
            r31AddClinicalChoice(labels,codes,"Frequenza da pressione","m|blood_pressure|heartRate|Frequenza da pressione");
        }else{
            r31AddClinicalChoice(labels,codes,"Pressione sistolica","m|blood_pressure|systolic|Pressione sistolica");
            r31AddClinicalChoice(labels,codes,"Pressione diastolica","m|blood_pressure|diastolic|Pressione diastolica");
            r31AddClinicalChoice(labels,codes,"Frequenza da pressione","m|blood_pressure|heartRate|Frequenza da pressione");
        }
        JSONArray labs=R27ExactWindows.availableLabParameters(prefs);
        for(int i=0;i<labs.length();i++){
            JSONObject p=labs.optJSONObject(i);if(p==null)continue;
            String id=p.optString("id","");if(id.isEmpty())continue;
            String label=p.optString("name",id);String unit=p.optString("unit","");if(!unit.isEmpty())label+=" ("+unit+")";
            r31AddClinicalChoice(labels,codes,label,"l|"+id+"|value|"+label);
        }
        if(labels.isEmpty()){Toast.makeText(this,"Nessun parametro disponibile",Toast.LENGTH_SHORT).show();return;}
        new AlertDialog.Builder(this).setTitle(graph?"Seleziona valore da visualizzare":"Seleziona valore da confrontare")
                .setItems(labels.toArray(new String[0]),(d,which)->{
                    prefs.edit().putString(graph?"r31_graph_choice":"r31_compare_choice",codes.get(which)).apply();
                    renderSection(graph?"Grafici":"Confronta");
                }).setNegativeButton("Annulla",null).show();
    }'''
s = replace_block(s, '    private void r31SelectClinicalValue(boolean graph) {', selector)

selected_graph = r'''    private void r31RenderSelectedGraph(String choice){
        if(choice!=null&&(choice.startsWith("p|blood_pressure|")||choice.contains("|blood_pressure|systolic|")||choice.contains("|blood_pressure|diastolic|"))){
            JSONArray rows=R27ExactWindows.measurementsOf(prefs,"blood_pressure");
            if(rows.length()==0){LinearLayout e=card();e.addView(text("Nessuna rilevazione pressoria disponibile.",13,MUTED,false));content.addView(e,matchWrapBottom(14));return;}
            LinearLayout c=card();c.addView(sectionHeader("Pressione arteriosa"));
            R33PressureChartView chart=new R33PressureChartView(this,rows,R27ExactWindows.activeProfileColor(prefs,GREEN));
            if(chart.hasData())c.addView(chart,new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,dp(255)));
            content.addView(c,matchWrapBottom(14));return;
        }
        JSONArray rows=r31SeriesForChoice(choice);
        if(rows.length()==0){LinearLayout e=card();e.addView(text("Nessuna rilevazione disponibile per il parametro selezionato.",13,MUTED,false));content.addView(e,matchWrapBottom(14));return;}
        r27Chart(r31ChoiceLabel(choice),rows,r31ChoiceKey(choice));
    }'''
s = replace_block(s, '    private void r31RenderSelectedGraph(String choice){', selected_graph)

# Add R33 helpers immediately before renderBackup, after all R31/R32 helpers are present.
insert = '    private void renderBackup() {'
if insert not in s:
    raise SystemExit('R33 patch failed: renderBackup insertion point missing')
helpers = r'''    private JSONArray r33ClinicalTimelineDocuments(){
        JSONArray docs=R27ExactWindows.documents(prefs),out=new JSONArray();
        for(int i=0;i<docs.length();i++){
            JSONObject d=docs.optJSONObject(i);if(d==null)continue;
            if(d.has("timelineVisible")&&!d.optBoolean("timelineVisible",true))continue;
            String source=d.optString("sourceSection","").toLowerCase(Locale.ROOT);
            if("calendar".equals(source)||"agenda".equals(source))continue;
            String hay=(r31First(d,"documentKind","category","type")+" "+r31First(d,"title","name","originalName")).toLowerCase(Locale.ROOT);
            if(hay.contains("prenot")||hay.contains("appuntamento")||hay.contains("agenda")||hay.contains("terapia")||hay.contains("farmaco")||hay.contains("ricetta")||hay.contains("prescrizion")||hay.contains("esenzion"))continue;
            boolean clinical=hay.contains("referto")||hay.contains("visita")||hay.contains("esame")||hay.contains("laboratorio")||hay.contains("strumentale")||hay.contains("radiolog")||hay.contains("ecograf")||hay.contains("risonanza")||hay.contains("tomografia")||hay.contains(" tac")||hay.contains("rx ")||hay.startsWith("rx")||hay.contains("diagnostica");
            if(clinical)out.put(d);
        }
        return out;
    }

    private void r33RenderWeightDetail(){
        r33MonitorDetailOpen=true;
        content.removeAllViews();
        viewTitle.setText("Percorso peso");
        viewSubtitle.setText("Percorso impostato, pesate pertinenti, traiettoria teorica e proiezione.");
        boolean oldestFirst=prefs.getBoolean("r32_monitor_weight_oldest_first",false);
        JSONArray rows=R27ExactWindows.measurementsOf(prefs,"weight");
        JSONObject journey=R33WeightJourneyModel.activeJourney(R27ExactWindows.weightJourneys(prefs));

        LinearLayout top=card();
        Button back=compactButton("← Torna a Monitoraggio");
        back.setOnClickListener(v->{r33MonitorDetailOpen=false;renderSection("Monitoraggio");});
        top.addView(back);
        Button order=button(oldestFirst?"Pesate: meno recenti prima":"Pesate: più recenti prima");
        order.setOnClickListener(v->{prefs.edit().putBoolean("r32_monitor_weight_oldest_first",!oldestFirst).apply();r33RenderWeightDetail();});
        top.addView(order,matchWrapTop(8));
        Button add=button("Aggiungi pesata");add.setOnClickListener(v->r31EditMeasurement("weight",null));top.addView(add,matchWrapTop(8));
        content.addView(top,matchWrapBottom(14));

        if(journey==null){
            LinearLayout e=card();e.addView(sectionHeader("Percorso peso"));e.addView(text("Nessun percorso peso impostato nel Dossier Windows.",13,MUTED,false));content.addView(e,matchWrapBottom(14));
            r33RenderWeightHistory(rows,oldestFirst,null);return;
        }

        R33WeightJourneyModel.Model model=R33WeightJourneyModel.build(rows,journey);
        if(model==null){
            LinearLayout e=card();e.addView(text("I dati del percorso peso importato non sono completi.",13,MUTED,false));content.addView(e,matchWrapBottom(14));
            r33RenderWeightHistory(rows,oldestFirst,journey);return;
        }
        double height=r33Number(journey,"heightCm");

        LinearLayout summary=card();summary.addView(sectionHeader("Percorso impostato"));
        r31AddIf(summary,"Data inizio",journey.optString("startDate",""));
        summary.addView(labelValue("Peso iniziale",R33WeightJourneyModel.weightBmi(model.startWeight,height)));
        summary.addView(labelValue("Peso attuale",R33WeightJourneyModel.weightBmi(model.latestWeight,height)));
        r31AddIf(summary,"Data obiettivo",journey.optString("targetDate",""));
        summary.addView(labelValue("Peso obiettivo",R33WeightJourneyModel.weightBmi(model.targetWeight,height)));
        if(Double.isFinite(height))summary.addView(labelValue("Altezza",R33WeightJourneyModel.fmt(height)+" cm"));
        r31AddIf(summary,"Sesso biologico usato dal calcolo",r33SexLabel(journey.optString("sex","")));
        r31AddIf(summary,"Livello di attività",r33ActivityLabel(journey.optString("activityLevel","")));
        r31AddIf(summary,"Stato",r33JourneyStatus(journey.optString("status","")));
        r31AddIf(summary,"Note",journey.optString("notes",""));
        ProgressBar progress=new ProgressBar(this,null,android.R.attr.progressBarStyleHorizontal);progress.setMax(1000);progress.setProgress((int)Math.round(model.progressPercent()*10));summary.addView(progress,matchWrapTop(10));
        summary.addView(labelValue("Avanzamento",String.format(Locale.ITALY,"%.1f%%",model.progressPercent())));
        summary.addView(labelValue("Giorni rimanenti",String.valueOf(model.daysRemaining())));
        summary.addView(labelValue("Variazione media richiesta",String.format(Locale.ITALY,"%.2f kg/settimana",model.weeklyRequired())));
        summary.addView(labelValue(r33GoalDistanceTitle(model),r33GoalDistanceValue(model)));
        content.addView(summary,matchWrapBottom(14));

        LinearLayout chartCard=card();chartCard.addView(sectionHeader("Andamento del percorso"));
        R33WeightJourneyChartView chart=new R33WeightJourneyChartView(this,rows,journey);
        if(chart.hasData())chartCard.addView(chart,new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,dp(315)));
        chartCard.addView(labelValue("Data obiettivo",journey.optString("targetDate","")));
        chartCard.addView(labelValue("Data stimata dal trend",model.predictedIso().isEmpty()?"Non stimabile":model.predictedIso()));
        String deviation=(model.pathDeviationKg>=0?"+":"")+String.format(Locale.ITALY,"%.2f kg",model.pathDeviationKg);
        chartCard.addView(labelValue("Scostamento dalla traiettoria",deviation));
        String delay=model.pathDelayDays==0?"In linea":(model.pathDelayDays>0?"In ritardo di "+model.pathDelayDays+" giorni":"In anticipo di "+Math.abs(model.pathDelayDays)+" giorni");
        chartCard.addView(labelValue("Scostamento temporale attuale",delay));
        if(model.forecastDeltaDays!=null){int fd=model.forecastDeltaDays;chartCard.addView(labelValue("Proiezione rispetto all'obiettivo",fd==0?"In linea con la data obiettivo":fd>0?"Stima +"+fd+" giorni":"Stima "+Math.abs(fd)+" giorni prima"));}
        content.addView(chartCard,matchWrapBottom(14));

        r33RenderBmiCalculator(model,height);
        r33RenderCalorieEstimate(model,journey,height);
        r33RenderWeightHistory(rows,oldestFirst,journey);
    }

    private void r33RenderWeightHistory(JSONArray rows,boolean oldestFirst,JSONObject journey){
        java.util.ArrayList<JSONObject> chronological=r31SortedByDate(rows,true,"date","createdAt","updatedAt");
        String startDate=journey==null?"":journey.optString("startDate","");
        java.util.ArrayList<JSONObject> pertinent=new java.util.ArrayList<>();
        for(JSONObject row:chronological){String date=r31First(row,"date","createdAt");if(startDate.isEmpty()||date.isEmpty()||date.compareTo(startDate)>=0)pertinent.add(row);}
        java.util.ArrayList<JSONObject> display=new java.util.ArrayList<>(pertinent);if(!oldestFirst)java.util.Collections.reverse(display);
        LinearLayout history=card();history.addView(sectionHeader("Storico pesate"));
        if(display.isEmpty()){history.addView(text("Nessuna pesata pertinente al percorso.",13,MUTED,false));content.addView(history,matchWrapBottom(14));return;}
        double first=r33Number(pertinent.get(0),"value");
        for(JSONObject row:display){
            int original=pertinent.indexOf(row);double value=r33Number(row,"value");double previous=original>0?r33Number(pertinent.get(original-1),"value"):value;
            LinearLayout line=new LinearLayout(this);line.setOrientation(LinearLayout.VERTICAL);line.setPadding(0,dp(7),0,dp(7));
            line.addView(text(r31Display(row,"date","createdAt")+"   "+R33WeightJourneyModel.fmt(value)+" kg",14,TEXT,true));
            line.addView(text("Diff. precedente "+r33Signed(value-previous)+" kg   ·   Diff. iniziale "+r33Signed(value-first)+" kg",12,MUTED,false));
            String note=row.optString("notes","");if(!note.isEmpty())line.addView(text(note,12,MUTED,false));
            Button edit=compactButton("Modifica");edit.setOnClickListener(v->r31EditMeasurement("weight",row));line.addView(edit,matchWrapTop(4));
            history.addView(line);
        }
        content.addView(history,matchWrapBottom(14));
    }

    private void r33RenderBmiCalculator(R33WeightJourneyModel.Model model,double height){
        LinearLayout c=card();c.addView(sectionHeader("Calcolatore BMI"));
        c.addView(text("Calcolo informativo: i valori inseriti qui non vengono salvati.",12,MUTED,false));
        EditText h=field("Altezza (cm)",Double.isFinite(height)?R33WeightJourneyModel.fmt(height):"");
        EditText w=field("Peso (kg)",R33WeightJourneyModel.fmt(model.latestWeight));
        TextView result=text("BMI: —",15,TEXT,true);Button calc=button("Calcola BMI");
        calc.setOnClickListener(v->{try{double hv=Double.parseDouble(clean(h).replace(',','.'));double wv=Double.parseDouble(clean(w).replace(',','.'));double bmi=R33WeightJourneyModel.bmi(wv,hv);result.setText(Double.isFinite(bmi)?"BMI: "+String.format(Locale.ITALY,"%.1f",bmi):"BMI: —");}catch(Exception ex){result.setText("BMI: —");}});
        c.addView(h);c.addView(w);c.addView(calc,matchWrapTop(7));c.addView(result,matchWrapTop(7));content.addView(c,matchWrapBottom(14));
    }

    private void r33RenderCalorieEstimate(R33WeightJourneyModel.Model model,JSONObject journey,double height){
        LinearLayout c=card();c.addView(sectionHeader("Stima calorica del percorso"));
        JSONObject profile=R27ExactWindows.activeProfile(prefs);String birth=profile==null?"":r31First(profile,"birthDate","birth");String sex=journey.optString("sex","");String activity=journey.optString("activityLevel","");
        int age=r33AgeAt(birth,journey.optString("startDate",""));
        if(age<=0||!Double.isFinite(height)||sex.isEmpty()||activity.isEmpty()){
            c.addView(text("Per la stima servono data di nascita, altezza, sesso biologico usato dal calcolo e livello di attività.",13,MUTED,false));content.addView(c,matchWrapBottom(14));return;
        }
        double bmr=10*model.latestWeight+6.25*height-5*age+("male".equalsIgnoreCase(sex)?5:-161);double factor=r33ActivityFactor(activity);double maintenance=bmr*factor;double direction=Math.signum(model.targetWeight-model.latestWeight);double dailyChange=Math.abs(model.targetWeight-model.latestWeight)*7700.0/Math.max(1.0,model.daysRemaining()>0?model.daysRemaining():model.daysTotal());double targetCalories=maintenance+direction*dailyChange;
        c.addView(labelValue("Mantenimento calorico stimato",Math.round(maintenance)+" kcal/giorno"));
        c.addView(labelValue("Apporto giornaliero stimato per il percorso",Math.round(targetCalories)+" kcal/giorno"));
        c.addView(labelValue("Variazione media di peso richiesta",String.format(Locale.ITALY,"%.2f kg/settimana",model.weeklyRequired())));
        c.addView(labelValue("Metabolismo a riposo stimato",Math.round(bmr)+" kcal/giorno"));
        c.addView(text("Stima matematica orientativa, non prescrizione medica o nutrizionale.",12,MUTED,false),matchWrapTop(7));
        if(direction<0&&(model.weeklyRequired()>1.0||targetCalories<1200))c.addView(text("Il ritmo o l'apporto stimato richiedono particolare prudenza e valutazione professionale.",12,MUTED,true),matchWrapTop(5));
        content.addView(c,matchWrapBottom(14));
    }

    private double r33Number(JSONObject row,String key){if(row==null)return Double.NaN;try{return Double.parseDouble(String.valueOf(row.opt(key)).replace(',','.').trim());}catch(Exception ex){return Double.NaN;}}
    private String r33Signed(double v){if(!Double.isFinite(v))return "—";return (v>0?"+":"")+String.format(Locale.ITALY,"%.1f",v);}
    private String r33SexLabel(String value){if("male".equalsIgnoreCase(value))return "Maschile";if("female".equalsIgnoreCase(value))return "Femminile";return value;}
    private String r33ActivityLabel(String value){if("sedentary".equalsIgnoreCase(value))return "Sedentario";if("light".equalsIgnoreCase(value))return "Leggermente attivo";if("moderate".equalsIgnoreCase(value))return "Moderatamente attivo";if("high".equalsIgnoreCase(value))return "Molto attivo";if("very_high".equalsIgnoreCase(value))return "Attività molto elevata";return value;}
    private String r33JourneyStatus(String value){if("active".equalsIgnoreCase(value))return "Attivo";if("paused".equalsIgnoreCase(value))return "Sospeso";if("completed".equalsIgnoreCase(value))return "Concluso";return value;}
    private String r33GoalDistanceTitle(R33WeightJourneyModel.Model m){double remaining=m.targetWeight-m.latestWeight;if(Math.abs(remaining)<0.05)return "Obiettivo raggiunto";boolean decreasing=m.targetWeight<m.startWeight;boolean passed=decreasing?m.latestWeight<m.targetWeight:m.latestWeight>m.targetWeight;return passed?"Obiettivo superato":"Mancano all'obiettivo";}
    private String r33GoalDistanceValue(R33WeightJourneyModel.Model m){return String.format(Locale.ITALY,"%.1f kg",Math.abs(m.targetWeight-m.latestWeight));}
    private int r33AgeAt(String birth,String reference){try{return java.time.Period.between(java.time.LocalDate.parse(birth),java.time.LocalDate.parse(reference)).getYears();}catch(Exception ex){return -1;}}
    private double r33ActivityFactor(String value){if("light".equalsIgnoreCase(value))return 1.375;if("moderate".equalsIgnoreCase(value))return 1.55;if("high".equalsIgnoreCase(value))return 1.725;if("very_high".equalsIgnoreCase(value))return 1.9;return 1.2;}

'''
s = s.replace(insert, helpers + insert, 1)

# Visible build identity only. Runtime approval still requires the Xiaomi test.
s = s.replace('Android R32 TEST COMPLETO','Android R33 TEST COMPLETO')
s = s.replace('Aiuto R32','Aiuto R33')

MAIN.write_text(s,encoding='utf-8')

g=GRADLE.read_text(encoding='utf-8')
if 'versionCode 32' not in g or "versionName '1.0.0-android-r32-ordering-monitor-test'" not in g:
    raise SystemExit('R33 patch failed: R32 version identity missing')
g=g.replace('versionCode 32','versionCode 33',1)
g=g.replace("versionName '1.0.0-android-r32-ordering-monitor-test'","versionName '1.0.0-android-r33-clinical-weight-parity-test'",1)
GRADLE.write_text(g,encoding='utf-8')
print('R33 clinical timeline, weight parity, combined pressure, landscape and monitor navigation patch applied')
