from pathlib import Path

MAIN = Path('android-r3/app/src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java')
s = MAIN.read_text(encoding='utf-8')


def replace_method(text, name, replacement):
    sig = f'    private void {name}() {{'
    start = text.find(sig)
    if start < 0: raise SystemExit(f'R31 tools patch failed: method {name} missing')
    brace = text.find('{', start); depth = 0; end = -1
    for i in range(brace, len(text)):
        if text[i] == '{': depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0: end = i + 1; break
    if end < 0: raise SystemExit(f'R31 tools patch failed: method {name} unclosed')
    return text[:start] + replacement.rstrip() + '\n' + text[end:]


def require(text, needle, label):
    if needle not in text: raise SystemExit(f'R31 tools patch failed: missing {label}')

compare = r'''    private void renderConfronta() {
        LinearLayout intro = card();
        intro.addView(sectionHeader("Confronta"));
        intro.addView(text("Scegli il valore da confrontare. Viene mostrato soltanto il parametro selezionato.", 13, MUTED, false));
        String selected = prefs.getString("r31_compare_choice", "");
        Button choose = button(selected.isEmpty() ? "Seleziona valore da confrontare" : "Cambia valore da confrontare");
        choose.setOnClickListener(v -> r31SelectClinicalValue(false));
        intro.addView(choose, matchWrapTop(9));
        content.addView(intro, matchWrapBottom(14));
        if (selected.isEmpty()) return;
        r31RenderSelectedComparison(selected);
    }'''
s = replace_method(s, 'renderConfronta', compare)

graphs = r'''    private void renderGrafici() {
        LinearLayout intro = card();
        intro.addView(sectionHeader("Grafici"));
        intro.addView(text("Seleziona il parametro clinico da visualizzare. Il grafico si apre soltanto per il valore scelto.", 13, MUTED, false));
        String selected = prefs.getString("r31_graph_choice", "");
        Button choose = button(selected.isEmpty() ? "Seleziona valore da visualizzare" : "Cambia valore da visualizzare");
        choose.setOnClickListener(v -> r31SelectClinicalValue(true));
        intro.addView(choose, matchWrapTop(9));
        content.addView(intro, matchWrapBottom(14));
        if (selected.isEmpty()) return;
        r31RenderSelectedGraph(selected);
    }'''
s = replace_method(s, 'renderGrafici', graphs)

agenda = r'''    private void renderAgenda() {
        JSONArray rows = R27ExactWindows.calendarEvents(prefs);
        LinearLayout intro = card();
        intro.addView(sectionHeader("Agenda"));
        intro.addView(labelValue("Eventi registrati", String.valueOf(rows.length())));
        Button add = button("Nuovo appuntamento"); add.setOnClickListener(v -> r31EditAgendaEvent(null)); intro.addView(add, matchWrapTop(8));
        Button sync = button("Sincronizza Agenda"); sync.setOnClickListener(v -> R12CloudManager.syncInteractiveR31(this, prefs)); intro.addView(sync, matchWrapTop(8));
        content.addView(intro, matchWrapBottom(14));
        java.util.ArrayList<JSONObject> ordered = r31SortedByDate(rows, false, "startDate", "date", "createdAt");
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
s = replace_method(s, 'renderAgenda', agenda)

monitor = r'''    private void renderMonitoraggio() {
        LinearLayout intro=card(); intro.addView(sectionHeader("Monitoraggio"));
        intro.addView(text("Apri la sezione desiderata per consultare lo storico e inserire manualmente nuove rilevazioni.",13,MUTED,false));
        content.addView(intro,matchWrapBottom(14));
        r31MonitorButton("Peso", "weight");
        r31MonitorButton("Misurazioni corporee", "body");
        r31MonitorButton("Pressione arteriosa", "blood_pressure");
        r31MonitorButton("Saturazione ossigeno", "spo2");
        r31MonitorButton("Glicemia", "glucose");
        r31MonitorButton("Frequenza cardiaca", "heart_rate");
    }'''
s = replace_method(s, 'renderMonitoraggio', monitor)

preferences = r'''    private void renderPreferenze() {
        JSONObject global=R27ExactWindows.globalPreferences(prefs); JSONObject profile=R27ExactWindows.profilePreferences(prefs);
        LinearLayout g=card(); g.addView(sectionHeader("Preferenze generali"));
        g.addView(labelValue("Colore del programma",r31PaletteLabel(global.optString("palette","teal"))));
        g.addView(labelValue("Aspetto",r31ThemeLabel(global.optString("theme","light"))));
        g.addView(labelValue("Dimensione del testo",r31TextScaleLabel(global.optString("textScale","normal"))));
        g.addView(labelValue("Spaziatura interfaccia",r31DensityLabel(global.optString("density","comfortable"))));
        g.addView(labelValue("Frequenza backup",r31BackupLabel(global.optString("backupFrequency","weekly"))));
        g.addView(labelValue("Conferma importazioni",global.optBoolean("confirmImports",true)?"Sì":"No"));
        g.addView(labelValue("E-mail Google Calendar",global.optString("googleCalendarEmail","").isEmpty()?"Non impostata":global.optString("googleCalendarEmail","")));
        g.addView(labelValue("Finestra raggruppamento riordino farmaci",global.optInt("medicationReorderGroupDays",7)+" giorni"));
        JSONArray reminders=global.optJSONArray("agendaDefaultReminders"); g.addView(labelValue("Avvisi Agenda predefiniti",reminders==null?"1440":r31JoinArray(reminders)));
        Button editGlobal=button("Modifica preferenze generali");editGlobal.setOnClickListener(v->r31EditGlobalPreferences(global));g.addView(editGlobal,matchWrapTop(10));
        content.addView(g,matchWrapBottom(14));

        LinearLayout p=card();p.addView(sectionHeader("Preferenze del profilo attivo"));
        p.addView(labelValue("Colore profilo",profile.optString("profileColor","#0f766e")));
        p.addView(labelValue("Vista Esenzioni","extended".equalsIgnoreCase(profile.optString("exemptionView","compact"))?"Estesa":"Compatta"));
        p.addView(labelValue("Vista Diagnosi","compact".equalsIgnoreCase(profile.optString("diagnosisView","extended"))?"Compatta":"Estesa"));
        p.addView(labelValue("Ordinamento Terapie",r31TherapySortLabel(profile.optString("therapySort","time-asc"))));
        p.addView(labelValue("Diagnosi nei PDF",r31DiagnosisPdfLabel(profile.optString("pdfDiagnosisMode","both"))));
        p.addView(labelValue("Includi Tessera Sanitaria",profile.optBoolean("includeHealthCard",true)?"Sì":"No"));
        p.addView(labelValue("Includi telefono medico",profile.optBoolean("includeDoctorPhone",true)?"Sì":"No"));
        p.addView(labelValue("PDF salvaspazio",profile.optBoolean("pdfSpaceSaving",false)?"Sì":"No"));
        p.addView(labelValue("Includi grafici nei PDF",profile.optBoolean("pdfIncludeGraphs",true)?"Sì":"No"));
        Button editProfile=button("Modifica preferenze del profilo");editProfile.setOnClickListener(v->r31EditProfilePreferences(profile));p.addView(editProfile,matchWrapTop(10));
        content.addView(p,matchWrapBottom(14));

        LinearLayout session=card();session.addView(sectionHeader("Sicurezza della sessione"));session.addView(labelValue("Blocco automatico",r26SessionTimeoutMinutes+" minuti"));
        Button timeout=button("Modifica tempo di blocco");timeout.setOnClickListener(v->r31EditTimeout());session.addView(timeout,matchWrapTop(8));content.addView(session,matchWrapBottom(14));
    }'''
s = replace_method(s, 'renderPreferenze', preferences)

help_method = r'''    private void renderAiuto() {
        LinearLayout c=card(); c.addView(sectionHeader("Aiuto"));
        c.addView(text("Guida pratica a Clinica Digitale - Dossier Sanitario, adattata anche all'uso su dispositivo mobile.",13,MUTED,false));
        c.addView(text("Protezione dei dati, GDPR e servizi esterni",15,TEXT,true),matchWrapTop(12));
        c.addView(text("Clinica Digitale è progettato secondo i principi di protezione dei dati personali e sanitari previsti dal GDPR, con archivio locale cifrato, credenziali personali e controlli di accesso. Il secondo fattore diventa obbligatorio quando il Dossier viene associato a un cloud esterno. Il cloud resta facoltativo e responsabilità, disponibilità e misure del provider restano soggette alle condizioni del servizio esterno e alla normativa applicabile.",13,MUTED,false),matchWrapTop(5));
        r31Help(c,"1. Che cos'è Clinica Digitale","Clinica Digitale raccoglie e organizza in un unico Dossier personale documenti, referti, terapie, diagnosi riportate nei documenti, valori di laboratorio, medici, appuntamenti e misurazioni. Il documento originale viene conservato insieme alle informazioni estratte, così puoi sempre risalire alla fonte.");
        r31Help(c,"2. Profili e account","Il profilo sanitario è la persona a cui appartengono i dati clinici. L'account è invece la persona che accede al programma. Ogni utente usa le proprie credenziali e i propri permessi. Password, codici temporanei e dati di recupero sono personali.");
        r31Help(c,"3. Dossier familiare e accesso ai dati di un altro adulto","Un Dossier familiare può comprendere più profili e più account. L'appartenenza alla famiglia non dà automaticamente diritto a leggere i dati sanitari di un altro adulto: l'accesso deve essere autorizzato e deve poter essere revocato. Gli altri utenti non devono conoscere le credenziali del provider cloud dell'amministratore.");
        r31Help(c,"4. Aggiungere un familiare","L'amministratore configura l'archivio cloud familiare e genera una sola password familiare di 15 caratteri, valida 48 ore e utilizzabile una sola volta. Non devono essere comunicati codici lunghi, UUID, chiavi o credenziali del provider. Il familiare usa la password, poi le proprie credenziali personali e, quando richiesto, il proprio secondo fattore TOTP.");
        r31Help(c,"5. Account familiari già esistenti","Un account familiare già creato non deve essere duplicato e mantiene il collegamento al profilo sanitario. Al primo adeguamento l'utente rende personali password e dati di recupero. Se non ricorda le vecchie credenziali, l'amministratore può reimpostare l'account esistente senza creare un secondo profilo.");
        r31Help(c,"6. Uscita dal Dossier familiare e migrazione del proprio profilo","Un adulto può esportare esclusivamente il proprio profilo e i relativi documenti, diagnosi, terapie, medici, monitoraggi, Agenda, tessera e storico necessari. L'esportazione non autorizza automaticamente la cancellazione dal Dossier di origine: soltanto la persona interessata, dopo aver verificato la migrazione, può autorizzare la rimozione.");
        r31Help(c,"7. Nuovo computer o altro dispositivo","Un utente già creato accede con il proprio account. L'autorizzazione riguarda la persona e i suoi permessi nel Dossier, non la conoscenza delle credenziali cloud. Dopo l'associazione prevista, i dispositivi autorizzati possono usare il Dossier senza configurare manualmente il provider della famiglia.");
        r31Help(c,"8. Importare documenti","Puoi importare PDF e immagini compatibili, comprese fotografie di documenti sanitari. Clinica Digitale tenta di riconoscere tipologia, specialità, data, struttura, medico e informazioni utili e conserva sempre l'originale. Le informazioni estratte possono essere controllate e, dove previsto, corrette manualmente.");
        r31Help(c,"9. Diagnosi","Clinica Digitale non formula diagnosi autonome. La sezione Diagnosi organizza diagnosi e condizioni riportate esplicitamente nei documenti oppure inserite manualmente. Quando il testo non consente un'attribuzione sicura, il dato resta da verificare.");
        r31Help(c,"10. Esami di laboratorio","I valori vengono mostrati insieme agli intervalli di riferimento presenti nel relativo referto. Se il documento non contiene un riferimento utilizzabile, il Dossier non applica automaticamente intervalli esterni per attribuire un significato diagnostico al risultato.");
        r31Help(c,"11. Terapie e archivio AIFA","La sezione Terapie organizza farmaci, dosaggi, orari, giorni di assunzione e note. L'archivio locale dei medicinali deriva dagli Open Data AIFA, licenza CC BY 4.0. Quando un nome può indicare più medicinali, il Dossier propone le corrispondenze e lascia scegliere quella corretta.");
        r31Help(c,"12. Dosaggi complessi","Puoi registrare quantità frazionarie, più assunzioni nella stessa giornata e giorni diversi della settimana. Per schemi con dosi differenti si registrano le dosi con i rispettivi giorni.");
        r31Help(c,"13. Scorte e riordino dei farmaci","Puoi indicare unità per confezione, confezioni disponibili, quantità assunta e data reale di inizio. Il Dossier calcola la scorta e prepara il promemoria prima dell'esaurimento. Farmaci con scadenze vicine possono essere raggruppati entro la finestra prevista.");
        r31Help(c,"14. Più somministrazioni dello stesso farmaco","Le impostazioni della scorta vengono condivise tra le righe dello stesso farmaco e dello stesso dosaggio. Il totale giornaliero va impostato una sola volta, così viene generato un solo conteggio e un solo promemoria.");
        r31Help(c,"15. Se cambia il piano terapeutico","Se il medico modifica quantità o giorni mentre una confezione è già iniziata, indica la decorrenza della modifica. Clinica Digitale conserva il consumo precedente, ricalcola la scorta residua e sposta il promemoria.");
        r31Help(c,"16. Agenda locale","L'Agenda funziona anche senza Internet, cloud o Google Calendar. Puoi registrare visite, esami, richieste, rinnovi e altre scadenze sanitarie, indicando data, ora, durata, luogo, note e avvisi.");
        r31Help(c,"17. Google Calendar: collegamento semplice","Nessun utente deve creare Client ID, secret o progetti tecnici. Inserisci l'indirizzo Google previsto nelle Preferenze e usa il collegamento autorizzato dall'app. Se non colleghi Google Calendar, l'Agenda locale continua a funzionare normalmente.");
        r31Help(c,"18. Dati inviati a Google Calendar","Quando autorizzi la sincronizzazione possono essere trasferiti i dati necessari all'evento, come titolo, profilo interessato, categoria, data, ora, durata, luogo, note, documento di origine e avvisi. La sincronizzazione dei nomi dei farmaci richiede un consenso separato.");
        r31Help(c,"19. Cloud e backup","Il cloud è facoltativo. Clinica Digitale continua a funzionare localmente anche senza collegamenti esterni. Con un provider compatibile, l'archivio cifrato può essere sincronizzato e ripristinato sui dispositivi autorizzati. Puoi inoltre creare backup locali indipendenti e conservarli in una posizione sicura.");
        r31Help(c,"20. Monitoraggio personale","Il peso e le pesate sono gestiti nel Percorso peso. Le Misurazioni corporee contengono circonferenze in centimetri. Pressione, frequenza cardiaca, saturazione e glicemia restano nei Parametri vitali. Grafici, BMI, stime e indicatori hanno funzione informativa e non costituiscono diagnosi o prescrizioni.");
        r31Help(c,"21. Versione per il medico e PDF","Quando disponibile, puoi preparare una copia ordinata del Dossier da mostrare al medico ed esportare le sezioni previste in PDF. Il documento esportato non modifica gli originali presenti nel Dossier.");
        r31Help(c,"22. Sicurezza e secondo fattore","Le password non vengono conservate in chiaro. Se hai attivato il codice temporaneo personale, utilizzi lo stesso Authenticator per accedere. Conserva separatamente gli eventuali codici di recupero. Il Logout termina la sessione ma non cancella il Dossier.");
        r31Help(c,"23. Segnalare un problema","La diagnostica tecnica deve essere sanitizzata e limitata ai dati necessari a individuare il malfunzionamento. Non deve contenere documenti sanitari, testi clinici, credenziali, nomi dei profili o percorsi dei file clinici.");
        r31Help(c,"24. FSE e portali sanitari","Clinica Digitale non utilizza scraping, aggiramenti o accessi non autorizzati al Fascicolo Sanitario Elettronico o ai portali regionali. In assenza di integrazione ufficiale, scarica normalmente il documento dal servizio sanitario e importalo nel Dossier.");
        r31Help(c,"25. Privacy e trattamento dei dati","Titolare del trattamento: Clinica Digitale, Pisa. Contatto privacy: dossiersanitario@gmail.com. Clinica Digitale adotta un'impostazione local-first. Cloud, Google Calendar e altri servizi esterni sono facoltativi e vengono utilizzati soltanto quando l'utente li attiva.");
        r31Help(c,"26. Se qualcosa non funziona","Non modificare manualmente i file interni del Dossier. Controlla lo stato dell'archivio, le modifiche eventualmente in attesa e le sincronizzazioni configurate. Una sincronizzazione non riuscita non significa automaticamente che i dati locali siano perduti. Per assistenza usa dossiersanitario@gmail.com.");
        content.addView(c,matchWrapBottom(14));
    }'''
s = replace_method(s, 'renderAiuto', help_method)

insert='    private void renderBackup() {'
require(s,insert,'renderBackup insertion point')
helpers=r'''    private void r31SelectClinicalValue(boolean graph) {
        java.util.ArrayList<String> labels=new java.util.ArrayList<>();java.util.ArrayList<String> codes=new java.util.ArrayList<>();
        r31AddClinicalChoice(labels,codes,"Peso","m|weight|value|Peso");
        r31AddClinicalChoice(labels,codes,"Saturazione ossigeno","m|spo2|value|Saturazione ossigeno");
        r31AddClinicalChoice(labels,codes,"Glicemia domestica","m|glucose|value|Glicemia domestica");
        r31AddClinicalChoice(labels,codes,"Frequenza cardiaca","m|heart_rate|value|Frequenza cardiaca");
        r31AddClinicalChoice(labels,codes,"Pressione sistolica","m|blood_pressure|systolic|Pressione sistolica");
        r31AddClinicalChoice(labels,codes,"Pressione diastolica","m|blood_pressure|diastolic|Pressione diastolica");
        r31AddClinicalChoice(labels,codes,"Frequenza da pressione","m|blood_pressure|heartRate|Frequenza da pressione");
        JSONArray labs=R27ExactWindows.availableLabParameters(prefs);for(int i=0;i<labs.length();i++){JSONObject p=labs.optJSONObject(i);if(p==null)continue;String id=p.optString("id","");if(id.isEmpty())continue;String label=p.optString("name",id);String unit=p.optString("unit","");if(!unit.isEmpty())label+=" ("+unit+")";r31AddClinicalChoice(labels,codes,label,"l|"+id+"|value|"+label);}
        if(labels.isEmpty()){Toast.makeText(this,"Nessun parametro disponibile",Toast.LENGTH_SHORT).show();return;}
        new AlertDialog.Builder(this).setTitle(graph?"Seleziona valore da visualizzare":"Seleziona valore da confrontare").setItems(labels.toArray(new String[0]),(d,which)->{prefs.edit().putString(graph?"r31_graph_choice":"r31_compare_choice",codes.get(which)).apply();renderSection(graph?"Grafici":"Confronta");}).setNegativeButton("Annulla",null).show();
    }

    private void r31AddClinicalChoice(java.util.ArrayList<String> labels,java.util.ArrayList<String> codes,String label,String code){labels.add(label);codes.add(code);}
    private JSONArray r31SeriesForChoice(String choice){String[] p=choice.split("\\|",4);if(p.length<4)return new JSONArray();return "l".equals(p[0])?R27ExactWindows.labSeries(prefs,p[1]):R27ExactWindows.measurementsOf(prefs,p[1]);}
    private String r31ChoiceLabel(String choice){String[] p=choice.split("\\|",4);return p.length>=4?p[3]:"Parametro";}
    private String r31ChoiceKey(String choice){String[] p=choice.split("\\|",4);return p.length>=3?p[2]:"value";}

    private void r31RenderSelectedComparison(String choice){
        JSONArray rows=r31SeriesForChoice(choice);String key=r31ChoiceKey(choice);LinearLayout c=card();c.addView(sectionHeader(r31ChoiceLabel(choice)));
        if(rows.length()<2){c.addView(text("Servono almeno due rilevazioni per eseguire il confronto.",13,MUTED,false));content.addView(c,matchWrapBottom(14));return;}
        JSONObject previous=rows.optJSONObject(rows.length()-2),latest=rows.optJSONObject(rows.length()-1);double a=R27ExactWindows.number(previous,key),b=R27ExactWindows.number(latest,key);
        if(Double.isNaN(a)||Double.isNaN(b)){c.addView(text("I valori disponibili non sono confrontabili.",13,MUTED,false));content.addView(c,matchWrapBottom(14));return;}
        c.addView(labelValue("Rilevazione precedente",formatR26Number(a)));c.addView(labelValue("Ultima rilevazione",formatR26Number(b)));c.addView(labelValue("Differenza",(b-a>=0?"+":"")+formatR26Number(b-a)));content.addView(c,matchWrapBottom(14));
    }
    private void r31RenderSelectedGraph(String choice){JSONArray rows=r31SeriesForChoice(choice);if(rows.length()==0){LinearLayout e=card();e.addView(text("Nessuna rilevazione disponibile per il parametro selezionato.",13,MUTED,false));content.addView(e,matchWrapBottom(14));return;}r27Chart(r31ChoiceLabel(choice),rows,r31ChoiceKey(choice));}

    private void r31EditAgendaEvent(JSONObject source){
        JSONObject base=source==null?new JSONObject():source;LinearLayout form=new LinearLayout(this);form.setOrientation(LinearLayout.VERTICAL);form.setPadding(dp(16),dp(8),dp(16),dp(8));
        EditText category=field("Tipo",r31CategoryItalian(base.optString("category","Visita")));EditText title=field("Titolo",base.optString("title",""));EditText date=field("Data (AAAA-MM-GG)",base.optString("startDate",""));EditText time=field("Ora (HH:MM)",base.optString("startTime",""));EditText duration=field("Durata in minuti",String.valueOf(base.optInt("durationMinutes",60)));EditText status=field("Stato",r31StatusItalian(base.optString("status","programmato")));EditText location=field("Luogo / struttura",base.optString("location",""));EditText notes=field("Note",base.optString("notes",""));JSONArray rem=base.optJSONArray("reminders");EditText reminders=field("Avvisi in minuti, separati da virgola",rem==null?"1440":r31JoinArray(rem));CheckBox allDay=r31Check("Tutto il giorno",base.optBoolean("allDay",false));
        for(EditText e:new EditText[]{category,title,date,time,duration,status,location,notes,reminders})form.addView(e);form.addView(allDay);ScrollView scroll=new ScrollView(this);scroll.addView(form);
        new AlertDialog.Builder(this).setTitle(source==null?"Nuovo appuntamento":"Modifica appuntamento").setView(scroll).setNegativeButton("Annulla",null).setPositiveButton("Salva",(d,w)->{try{JSONObject updated=new JSONObject(base.toString());if(updated.optString("id","").isEmpty())updated.put("id","calevent_android_"+System.currentTimeMillis());updated.put("profileId",R27ExactWindows.activeProfileId(prefs));updated.put("category",clean(category));updated.put("title",clean(title));updated.put("startDate",clean(date));updated.put("startTime",clean(time));updated.put("durationMinutes",r31Int(clean(duration),60));updated.put("allDay",allDay.isChecked());updated.put("status",r31AgendaStatusCode(clean(status)));updated.put("location",clean(location));updated.put("notes",clean(notes));updated.put("reminders",r31IntArray(clean(reminders)));if(!R27ExactWindows.upsertData(prefs,"calendarEvents",updated))throw new Exception("dati non salvati");R12CloudManager.queueR31EntityPut(this,prefs,"calendarEvents",updated);renderSection("Agenda");}catch(Exception failure){Toast.makeText(this,"Salvataggio appuntamento non riuscito",Toast.LENGTH_LONG).show();}}).show();
    }
    private int r31Int(String value,int fallback){try{return Integer.parseInt(value.trim());}catch(Exception e){return fallback;}}
    private JSONArray r31IntArray(String csv){JSONArray out=new JSONArray();for(String part:String.valueOf(csv).split(",")){try{out.put(Integer.parseInt(part.trim()));}catch(Exception ignored){}}return out;}
    private String r31AgendaStatusCode(String raw){String s=String.valueOf(raw).trim().toLowerCase(Locale.ROOT);if(s.startsWith("complet"))return"completed";if(s.startsWith("annull"))return"cancelled";return"planned";}

    private void r31MonitorButton(String label,String type){LinearLayout c=card();c.addView(text(label,16,TEXT,true));JSONArray rows="body".equals(type)?r31BodyMeasurements():R27ExactWindows.measurementsOf(prefs,type);c.addView(labelValue("Rilevazioni",String.valueOf(rows.length())));Button open=button("Apri "+label);open.setOnClickListener(v->r31RenderMonitorDetail(type,label));c.addView(open,matchWrapTop(8));content.addView(c,matchWrapBottom(10));}
    private JSONArray r31BodyMeasurements(){JSONArray all=R27ExactWindows.measurements(prefs),out=new JSONArray();for(int i=0;i<all.length();i++){JSONObject r=all.optJSONObject(i);if(r!=null&&r31IsBodyType(r.optString("type","")))out.put(r);}return out;}
    private boolean r31IsBodyType(String type){String[] keys={"height","neck","chest","waist","abdomen","hips","arm_right","arm_left","thigh_right","thigh_left","calf_right","calf_left","wrist_right","wrist_left","ankle_right","ankle_left"};for(String k:keys)if(k.equals(type))return true;return false;}
    private String r31BodyLabel(String type){String[] k={"height","neck","chest","waist","abdomen","hips","arm_right","arm_left","thigh_right","thigh_left","calf_right","calf_left","wrist_right","wrist_left","ankle_right","ankle_left"};String[] l={"Altezza","Collo","Petto / torace","Vita","Addome","Fianchi","Braccio destro","Braccio sinistro","Coscia destra","Coscia sinistra","Polpaccio destro","Polpaccio sinistro","Polso destro","Polso sinistro","Caviglia destra","Caviglia sinistra"};for(int i=0;i<k.length;i++)if(k[i].equals(type))return l[i];return type;}

    private void r31RenderMonitorDetail(String type,String label){
        content.removeAllViews();viewTitle.setText(label);viewSubtitle.setText("Storico e inserimento manuale delle rilevazioni.");
        LinearLayout top=card();Button back=compactButton("← Torna a Monitoraggio");back.setOnClickListener(v->renderSection("Monitoraggio"));top.addView(back);Button add=button("Aggiungi rilevazione");add.setOnClickListener(v->{if("body".equals(type))r31ChooseBodyMeasurement();else r31EditMeasurement(type,null);});top.addView(add,matchWrapTop(8));content.addView(top,matchWrapBottom(14));
        JSONArray rows="body".equals(type)?r31BodyMeasurements():R27ExactWindows.measurementsOf(prefs,type);java.util.ArrayList<JSONObject> ordered=r31SortedByDate(rows,false,"date","createdAt","updatedAt");
        if(ordered.isEmpty()){LinearLayout e=card();e.addView(text("Nessuna rilevazione registrata.",13,MUTED,false));content.addView(e,matchWrapBottom(14));return;}
        for(JSONObject row:ordered){LinearLayout c=card();String rowLabel="body".equals(type)?r31BodyLabel(row.optString("type","")):label;c.addView(text(rowLabel,15,TEXT,true));r31AddIf(c,"Data",r31First(row,"date","createdAt"));r31AddIf(c,"Ora",row.optString("time",""));if("blood_pressure".equals(type)){r31AddIf(c,"Sistolica",row.optString("systolic",""));r31AddIf(c,"Diastolica",row.optString("diastolic",""));r31AddIf(c,"Frequenza cardiaca",row.optString("heartRate",""));}else{r31AddIf(c,"Valore",row.optString("value","")+(row.optString("unit","").isEmpty()?"":" "+row.optString("unit","")));}r31AddIf(c,"Contesto",row.optString("context",""));r31AddIf(c,"Dispositivo",row.optString("device",""));r31AddIf(c,"Note",row.optString("notes",""));Button edit=compactButton("Modifica");String actual=row.optString("type",type);edit.setOnClickListener(v->r31EditMeasurement(actual,row));c.addView(edit,matchWrapTop(7));content.addView(c,matchWrapBottom(9));}
    }

    private void r31ChooseBodyMeasurement(){String[] codes={"height","neck","chest","waist","abdomen","hips","arm_right","arm_left","thigh_right","thigh_left","calf_right","calf_left","wrist_right","wrist_left","ankle_right","ankle_left"};String[] labels=new String[codes.length];for(int i=0;i<codes.length;i++)labels[i]=r31BodyLabel(codes[i]);new AlertDialog.Builder(this).setTitle("Misurazione corporea").setItems(labels,(d,which)->r31EditMeasurement(codes[which],null)).setNegativeButton("Annulla",null).show();}

    private void r31EditMeasurement(String type,JSONObject source){
        JSONObject base=source==null?new JSONObject():source;LinearLayout form=new LinearLayout(this);form.setOrientation(LinearLayout.VERTICAL);form.setPadding(dp(16),dp(8),dp(16),dp(8));
        EditText date=field("Data (AAAA-MM-GG)",base.optString("date",new SimpleDateFormat("yyyy-MM-dd",Locale.ROOT).format(new Date())));EditText time=field("Ora (HH:MM)",base.optString("time",new SimpleDateFormat("HH:mm",Locale.ROOT).format(new Date())));form.addView(date);form.addView(time);
        EditText value=null,systolic=null,diastolic=null,heart=null,unit=null;
        if("blood_pressure".equals(type)){systolic=field("Pressione sistolica",base.optString("systolic",""));diastolic=field("Pressione diastolica",base.optString("diastolic",""));heart=field("Frequenza cardiaca",base.optString("heartRate",""));form.addView(systolic);form.addView(diastolic);form.addView(heart);}else{String hint="weight".equals(type)?"Peso (kg)":"spo2".equals(type)?"Saturazione SpO₂ (%)":"glucose".equals(type)?"Glicemia":"heart_rate".equals(type)?"Frequenza cardiaca":r31BodyLabel(type)+" (cm)";value=field(hint,base.optString("value",""));form.addView(value);if("glucose".equals(type)){unit=field("Unità (mg/dL o mmol/L)",base.optString("unit","mg/dL"));form.addView(unit);}if("spo2".equals(type)){heart=field("Frequenza cardiaca",base.optString("heartRate",""));form.addView(heart);}}
        EditText context=field("Contesto",base.optString("context",""));EditText device=field("Dispositivo",base.optString("device",""));EditText notes=field("Note",base.optString("notes",""));form.addView(context);form.addView(device);form.addView(notes);ScrollView scroll=new ScrollView(this);scroll.addView(form);
        final EditText fv=value,fs=systolic,fd=diastolic,fh=heart,fu=unit;
        new AlertDialog.Builder(this).setTitle(source==null?"Aggiungi rilevazione":"Modifica rilevazione").setView(scroll).setNegativeButton("Annulla",null).setPositiveButton("Salva",(d,w)->{try{JSONObject updated=new JSONObject(base.toString());if(updated.optString("id","").isEmpty())updated.put("id","measurement_android_"+System.currentTimeMillis());updated.put("profileId",R27ExactWindows.activeProfileId(prefs));updated.put("type",type);updated.put("date",clean(date));updated.put("time",clean(time));if("blood_pressure".equals(type)){updated.put("systolic",clean(fs));updated.put("diastolic",clean(fd));updated.put("heartRate",clean(fh));updated.put("unit","mmHg");}else{updated.put("value",clean(fv));updated.put("unit",fu!=null?clean(fu):"weight".equals(type)?"kg":r31IsBodyType(type)?"cm":"spo2".equals(type)?"%":"heart_rate".equals(type)?"bpm":base.optString("unit",""));if(fh!=null)updated.put("heartRate",clean(fh));}updated.put("context",clean(context));updated.put("device",clean(device));updated.put("notes",clean(notes));if(!R27ExactWindows.upsertData(prefs,"measurements",updated))throw new Exception("dati non salvati");R12CloudManager.queueR31EntityPut(this,prefs,"measurements",updated);r31RenderMonitorDetail(r31IsBodyType(type)?"body":type,r31IsBodyType(type)?"Misurazioni corporee":"blood_pressure".equals(type)?"Pressione arteriosa":"spo2".equals(type)?"Saturazione ossigeno":"glucose".equals(type)?"Glicemia":"heart_rate".equals(type)?"Frequenza cardiaca":"Peso");}catch(Exception failure){Toast.makeText(this,"Salvataggio rilevazione non riuscito",Toast.LENGTH_LONG).show();}}).show();
    }

    private String r31PaletteLabel(String v){if("green".equals(v))return"Verde";if("blue".equals(v))return"Blu";if("burgundy".equals(v))return"Bordeaux";if("violet".equals(v))return"Viola";if("graphite".equals(v))return"Grafite";return"Verde petrolio";}
    private String r31ThemeLabel(String v){return"dark".equals(v)?"Scuro":"Chiaro";}
    private String r31TextScaleLabel(String v){return"large".equals(v)?"Grande":"small".equals(v)?"Piccola":"Normale";}
    private String r31DensityLabel(String v){return"compact".equals(v)?"Compatta":"Spaziosa";}
    private String r31BackupLabel(String v){return"daily".equals(v)?"Giornaliera":"monthly".equals(v)?"Mensile":"manual".equals(v)?"Manuale":"Settimanale";}
    private String r31TherapySortLabel(String v){return"name-asc".equals(v)?"Per farmaco":"time-desc".equals(v)?"Orario decrescente":"Orario crescente";}
    private String r31DiagnosisPdfLabel(String v){return"compact".equals(v)?"Solo compatta":"extended".equals(v)?"Solo estesa":"Compatta ed estesa";}
    private String r31JoinArray(JSONArray a){StringBuilder b=new StringBuilder();for(int i=0;i<a.length();i++){if(i>0)b.append(", ");b.append(a.optString(i,""));}return b.toString();}

    private void r31EditGlobalPreferences(JSONObject source){
        JSONObject base=source==null?new JSONObject():source;LinearLayout form=new LinearLayout(this);form.setOrientation(LinearLayout.VERTICAL);form.setPadding(dp(16),dp(8),dp(16),dp(8));
        EditText palette=field("Colore programma: teal, green, blue, burgundy, violet, graphite",base.optString("palette","teal"));EditText theme=field("Aspetto: light o dark",base.optString("theme","light"));EditText textScale=field("Dimensione testo: small, normal o large",base.optString("textScale","normal"));EditText density=field("Spaziatura: comfortable o compact",base.optString("density","comfortable"));EditText backup=field("Frequenza backup: daily, weekly, monthly o manual",base.optString("backupFrequency","weekly"));EditText google=field("E-mail Google Calendar",base.optString("googleCalendarEmail",""));EditText reorder=field("Giorni raggruppamento riordino (massimo 10)",String.valueOf(base.optInt("medicationReorderGroupDays",7)));JSONArray rem=base.optJSONArray("agendaDefaultReminders");EditText reminders=field("Avvisi Agenda in minuti",rem==null?"1440":r31JoinArray(rem));CheckBox confirm=r31Check("Chiedi conferma prima delle importazioni",base.optBoolean("confirmImports",true));
        for(EditText e:new EditText[]{palette,theme,textScale,density,backup,google,reorder,reminders})form.addView(e);form.addView(confirm);ScrollView scroll=new ScrollView(this);scroll.addView(form);
        new AlertDialog.Builder(this).setTitle("Modifica preferenze generali").setView(scroll).setNegativeButton("Annulla",null).setPositiveButton("Salva",(d,w)->{try{JSONObject updated=new JSONObject(base.toString());updated.put("palette",r31Allowed(clean(palette),new String[]{"teal","green","blue","burgundy","violet","graphite"},"teal"));updated.put("theme",r31Allowed(clean(theme),new String[]{"light","dark"},"light"));updated.put("textScale",r31Allowed(clean(textScale),new String[]{"small","normal","large"},"normal"));updated.put("density",r31Allowed(clean(density),new String[]{"comfortable","compact"},"comfortable"));updated.put("backupFrequency",r31Allowed(clean(backup),new String[]{"daily","weekly","monthly","manual"},"weekly"));updated.put("googleCalendarEmail",clean(google));updated.put("medicationReorderGroupDays",Math.max(0,Math.min(10,r31Int(clean(reorder),7))));updated.put("agendaDefaultReminders",r31IntArray(clean(reminders)));updated.put("confirmImports",confirm.isChecked());R27ExactWindows.updateGlobalPreferences(prefs,updated);JSONObject entity=new JSONObject();entity.put("id","globalPreferences");entity.put("key","globalPreferences");entity.put("value",updated);R12CloudManager.queueR31EntityPut(this,prefs,"settings",entity);loadR26ImportedUiSettings();showMainUi(null);renderSection("Preferenze");}catch(Exception failure){Toast.makeText(this,"Salvataggio preferenze non riuscito",Toast.LENGTH_LONG).show();}}).show();
    }
    private String r31Allowed(String value,String[] allowed,String fallback){for(String a:allowed)if(a.equalsIgnoreCase(value))return a;return fallback;}

    private void r31EditProfilePreferences(JSONObject source){
        JSONObject base=source==null?new JSONObject():source;LinearLayout form=new LinearLayout(this);form.setOrientation(LinearLayout.VERTICAL);form.setPadding(dp(16),dp(8),dp(16),dp(8));
        EditText color=field("Colore profilo (#RRGGBB)",base.optString("profileColor","#0f766e"));EditText exemption=field("Vista Esenzioni: compact o extended",base.optString("exemptionView","compact"));EditText diagnosis=field("Vista Diagnosi: compact o extended",base.optString("diagnosisView","extended"));EditText therapySort=field("Ordine Terapie: time-asc, time-desc o name-asc",base.optString("therapySort","time-asc"));EditText pdfDiagnosis=field("Diagnosi PDF: both, compact o extended",base.optString("pdfDiagnosisMode","both"));CheckBox health=r31Check("Includi Tessera Sanitaria",base.optBoolean("includeHealthCard",true));CheckBox doctorPhone=r31Check("Includi telefono medico",base.optBoolean("includeDoctorPhone",true));CheckBox saving=r31Check("PDF salvaspazio",base.optBoolean("pdfSpaceSaving",false));CheckBox graphs=r31Check("Includi grafici nei PDF",base.optBoolean("pdfIncludeGraphs",true));
        for(EditText e:new EditText[]{color,exemption,diagnosis,therapySort,pdfDiagnosis})form.addView(e);for(CheckBox c:new CheckBox[]{health,doctorPhone,saving,graphs})form.addView(c);ScrollView scroll=new ScrollView(this);scroll.addView(form);
        new AlertDialog.Builder(this).setTitle("Modifica preferenze del profilo").setView(scroll).setNegativeButton("Annulla",null).setPositiveButton("Salva",(d,w)->{try{JSONObject updated=new JSONObject(base.toString());String hex=clean(color);if(!hex.matches("#[0-9A-Fa-f]{6}"))hex="#0f766e";updated.put("profileColor",hex);updated.put("exemptionView",r31Allowed(clean(exemption),new String[]{"compact","extended"},"compact"));updated.put("diagnosisView",r31Allowed(clean(diagnosis),new String[]{"compact","extended"},"extended"));updated.put("therapySort",r31Allowed(clean(therapySort),new String[]{"time-asc","time-desc","name-asc"},"time-asc"));updated.put("pdfDiagnosisMode",r31Allowed(clean(pdfDiagnosis),new String[]{"both","compact","extended"},"both"));updated.put("includeHealthCard",health.isChecked());updated.put("includeDoctorPhone",doctorPhone.isChecked());updated.put("pdfSpaceSaving",saving.isChecked());updated.put("pdfIncludeGraphs",graphs.isChecked());R27ExactWindows.updateProfilePreferences(prefs,updated);JSONObject profile=R27ExactWindows.activeProfile(prefs);if(profile!=null)R12CloudManager.queueR31EntityPut(this,prefs,"profiles",profile);loadR26ImportedUiSettings();showMainUi(null);renderSection("Preferenze");}catch(Exception failure){Toast.makeText(this,"Salvataggio preferenze non riuscito",Toast.LENGTH_LONG).show();}}).show();
    }

    private void r31EditTimeout(){EditText minutes=field("Minuti prima del blocco automatico",String.valueOf(r26SessionTimeoutMinutes));new AlertDialog.Builder(this).setTitle("Blocco automatico").setView(minutes).setNegativeButton("Annulla",null).setPositiveButton("Salva",(d,w)->{int value=Math.max(1,Math.min(240,r31Int(clean(minutes),15)));prefs.edit().putInt("r26_timeout_override",value).apply();r26SessionTimeoutMinutes=value;scheduleR26TimeoutCheck();renderSection("Preferenze");}).show();}
    private void r31Help(LinearLayout parent,String title,String body){parent.addView(text(title,14,TEXT,true),matchWrapTop(13));parent.addView(text(body,13,MUTED,false),matchWrapTop(4));}

'''
s=s.replace(insert,helpers+insert,1)
MAIN.write_text(s,encoding='utf-8')
print('R31 compare, graphs, agenda, monitoring, preferences and help patch applied')
