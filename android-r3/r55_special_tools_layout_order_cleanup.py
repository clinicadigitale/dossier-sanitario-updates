from pathlib import Path
import re

base = Path('android-r3/app/src/main/java/it/dossiersanitario/clinicadigitale/beta')
activity_path = base / 'R53SpecialToolsActivity.java'
activity = activity_path.read_text(encoding='utf-8')

# R55 is deliberately limited to the R53/R54 special-tools UI shell and ordering.
# Clinical selection/search logic and every established R52/R53 engine remain untouched.

if 'import android.content.res.Configuration;' not in activity:
    activity = activity.replace('import android.content.Context;\n', 'import android.content.Context;\nimport android.content.res.Configuration;\n', 1)
if 'import android.widget.ImageView;' not in activity:
    activity = activity.replace('import android.widget.EditText;\n', 'import android.widget.EditText;\nimport android.widget.ImageView;\n', 1)

new_base = r'''    private View basePage(String title, String subtitle) {
        LinearLayout root=new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(GREEN_DARK);
        root.setFitsSystemWindows(false);
        root.setOnApplyWindowInsetsListener((v,insets)->{
            int top=insets.getSystemWindowInsetTop();
            int bottom=insets.getSystemWindowInsetBottom();
            boolean landscape=getResources().getConfiguration().orientation==Configuration.ORIENTATION_LANDSCAPE;
            int left=landscape?insets.getSystemWindowInsetLeft():0;
            int right=landscape?insets.getSystemWindowInsetRight():0;
            v.setPadding(left,top,right,bottom);
            return insets;
        });

        ScrollView main=new ScrollView(this);
        main.setFillViewport(true);
        main.setBackgroundColor(PAGE);

        LinearLayout page=new LinearLayout(this);
        page.setOrientation(LinearLayout.VERTICAL);
        page.setBackgroundColor(PAGE);

        LinearLayout header=new LinearLayout(this);
        header.setOrientation(LinearLayout.HORIZONTAL);
        header.setGravity(Gravity.CENTER_VERTICAL);
        header.setPadding(dp(10),dp(5),dp(10),dp(5));
        header.setBackgroundColor(GREEN);

        ImageView icon=new ImageView(this);
        icon.setImageResource(R.drawable.dossier_sanitario);
        icon.setScaleType(ImageView.ScaleType.FIT_CENTER);
        header.addView(icon,new LinearLayout.LayoutParams(dp(92),dp(92)));

        TextView appTitle=text("Dossier Sanitario",24,Color.WHITE,true);
        appTitle.setPadding(dp(8),0,0,0);
        header.addView(appTitle,new LinearLayout.LayoutParams(0,ViewGroup.LayoutParams.WRAP_CONTENT,1f));

        Button sections=compactButton("☰  Sezioni");
        sections.setTextColor(Color.WHITE);
        sections.setBackground(roundRect(Color.argb(38,255,255,255),Color.argb(80,255,255,255),10));
        sections.setOnClickListener(v->showSectionsDialog());
        header.addView(sections,new LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT,dp(46)));
        page.addView(header);

        LinearLayout profileBar=new LinearLayout(this);
        profileBar.setOrientation(LinearLayout.HORIZONTAL);
        profileBar.setGravity(Gravity.CENTER_VERTICAL);
        profileBar.setPadding(dp(16),dp(9),dp(16),dp(9));
        profileBar.setBackgroundColor(Color.WHITE);
        profileBar.addView(text("Profilo attivo",12,MUTED,false));
        TextView profile=text(R27ExactWindows.activeProfileName(prefs),14,TEXT,true);
        profile.setGravity(Gravity.END);
        profileBar.addView(profile,new LinearLayout.LayoutParams(0,ViewGroup.LayoutParams.WRAP_CONTENT,1f));
        profileBar.setOnClickListener(v->showProfilePickerR55());
        page.addView(profileBar);

        LinearLayout topbar=new LinearLayout(this);
        topbar.setOrientation(LinearLayout.VERTICAL);
        topbar.setPadding(dp(16),dp(13),dp(16),dp(12));
        topbar.setBackgroundColor(PAGE);
        TextView pageTitle=text(title,24,TEXT,true);
        TextView pageSubtitle=text(subtitle,13,MUTED,false);
        pageSubtitle.setPadding(0,dp(3),0,0);
        topbar.addView(pageTitle);
        topbar.addView(pageSubtitle);
        page.addView(topbar);

        content=new LinearLayout(this);
        content.setOrientation(LinearLayout.VERTICAL);
        content.setPadding(dp(16),dp(4),dp(16),dp(28));
        content.setBackgroundColor(PAGE);
        page.addView(content,new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,ViewGroup.LayoutParams.WRAP_CONTENT));

        main.addView(page,new ScrollView.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,ViewGroup.LayoutParams.WRAP_CONTENT));
        root.addView(main,new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,0,1f));
        return root;
    }

    private void showProfilePickerR55(){
        JSONArray profiles=R27ExactWindows.profiles(prefs);
        if(profiles==null||profiles.length()==0)return;
        String[] labels=new String[profiles.length()];
        int selected=0;
        String current=R27ExactWindows.activeProfileId(prefs);
        for(int i=0;i<profiles.length();i++){
            JSONObject p=profiles.optJSONObject(i);
            labels[i]=p==null?"Profilo":R53VisitLogic.first(p,"name","displayName","fullName");
            if(labels[i].isEmpty())labels[i]="Profilo";
            if(p!=null&&current.equals(p.optString("id","")))selected=i;
        }
        new AlertDialog.Builder(this).setTitle("Cambia profilo").setSingleChoiceItems(labels,selected,(dialog,which)->{
            JSONObject p=profiles.optJSONObject(which);
            if(p==null)return;
            R27ExactWindows.setActiveProfile(prefs,p.optString("id",""));
            dialog.dismiss();
            loadTheme();
            getWindow().setStatusBarColor(GREEN_DARK);
            recreate();
        }).setNegativeButton("Chiudi",null).show();
    }'''

pattern = re.compile(r'    private View basePage\(String title, String subtitle\) \{.*?\n    \}\n\n    private View buildPrepareUi\(\) \{', re.S)
match = pattern.search(activity)
if not match:
    raise SystemExit('R55 basePage anchor not found')
activity = activity[:match.start()] + new_base + '\n\n    private View buildPrepareUi() {' + activity[match.end():]

new_prepare = r'''    private View buildPrepareUi() {
        View page=basePage("Prepara una visita","Raccolta deterministica dei dati del Dossier. Nessuna intelligenza artificiale e nessuna modifica ai documenti originali.");
        LinearLayout setup=card(); setup.addView(sectionHeader("Visita"));
        specialtySpinner=new Spinner(this); List<String> specs=availableSpecialties(); specialtySpinner.setAdapter(adapter(specs)); setup.addView(specialtySpinner,matchWrapTop(4));
        dateButton=button("Data visita: "+visitDate); dateButton.setOnClickListener(v->chooseDate()); setup.addView(dateButton,matchWrapTop(8));
        diagnosisSpinner=new Spinner(this); setup.addView(label("Patologia / diagnosi specifica (facoltativa)"),matchWrapTop(10)); setup.addView(diagnosisSpinner); refreshDiagnosisSpinner();
        Button prepare=button("Prepara"); prepare.setOnClickListener(v->prepare()); setup.addView(prepare,matchWrapTop(10)); content.addView(setup,matchWrapBottom(14));

        directBox=card(); directBox.addView(sectionHeader("Documenti associati")); directBox.addView(text("I documenti già identificati con patologia o specialità vengono selezionati automaticamente, ma puoi escluderli.",13,MUTED,false)); content.addView(directBox,matchWrapBottom(14));
        proposedBox=card(); proposedBox.addView(sectionHeader("Documenti proposti")); proposedBox.addView(text("Possibili documenti pertinenti, compresi gli ultimi prelievi. Non vengono selezionati automaticamente.",13,MUTED,false)); content.addView(proposedBox,matchWrapBottom(14));
        manualBox=card(); manualBox.addView(sectionHeader("Altri documenti scelti da te")); Button addDoc=button("Aggiungi dal Dossier"); addDoc.setOnClickListener(v->showManualDocumentPicker()); manualBox.addView(addDoc); content.addView(manualBox,matchWrapBottom(14));

        LinearLayout req=card(); req.addView(sectionHeader("Cose da chiedere"));
        requestType=new Spinner(this); requestType.setAdapter(adapter(java.util.Arrays.asList("Ricetta / impegnativa","Visita specialistica","Esame","Farmaco","Domanda al medico","Altro"))); req.addView(requestType);
        requestText=new EditText(this); requestText.setHint("Scrivi la richiesta"); requestText.setMinLines(2); req.addView(requestText,matchWrapTop(6)); Button addReq=button("Aggiungi richiesta"); addReq.setOnClickListener(v->addRequest()); req.addView(addReq,matchWrapTop(8)); requestBox=new LinearLayout(this); requestBox.setOrientation(LinearLayout.VERTICAL); req.addView(requestBox,matchWrapTop(8)); content.addView(req,matchWrapBottom(14));

        medicationBox=card(); medicationBox.addView(sectionHeader("Farmaci da richiedere")); medicationBox.addView(text("Per Medico di base vengono mostrati soltanto i farmaci da richiedere secondo la finestra già impostata nelle Preferenze.",13,MUTED,false)); content.addView(medicationBox,matchWrapBottom(14));

        LinearLayout actions=card(); actions.addView(sectionHeader("Esporta o stampa fascicolo"));
        actions.addView(text("Dopo aver scelto i documenti e completato la preparazione, genera il riepilogo della visita o esporta gli originali selezionati.",13,MUTED,false));
        Button pdf=button("Esporta PDF"); pdf.setOnClickListener(v->startExportPdf()); actions.addView(pdf,matchWrapTop(8));
        Button print=button("Stampa"); print.setOnClickListener(v->printSummary()); actions.addView(print,matchWrapTop(8));
        Button export=compactButton("Esporta documenti originali"); export.setOnClickListener(v->startExportZip()); actions.addView(export,matchWrapTop(8));
        Button reset=compactButton("Azzera preparazione"); reset.setOnClickListener(v->resetPreparation()); actions.addView(reset,matchWrapTop(8)); content.addView(actions,matchWrapBottom(14));

        prepare(); return page;
    }'''

pattern = re.compile(r'    private View buildPrepareUi\(\) \{.*?\n    \}\n\n    private View buildSearchUi\(\) \{', re.S)
match = pattern.search(activity)
if not match:
    raise SystemExit('R55 buildPrepareUi anchor not found')
activity = activity[:match.start()] + new_prepare + '\n\n    private View buildSearchUi() {' + activity[match.end():]

activity, count = re.subn(
    r'    private int windowDays\(\)\{.*?\}\n',
    '    private int windowDays(){JSONObject g=R27ExactWindows.globalPreferences(prefs);return Math.max(1,Math.min(10,g.optInt("medicationReorderGroupDays",7)));}\n',
    activity,
    count=1,
)
if count != 1:
    raise SystemExit('R55 windowDays anchor not found')

activity, count = re.subn(
    r'    private void resetPreparation\(\)\{.*?\}\n',
    '    private void resetPreparation(){manualDocs.clear();requests.clear();renderRequests();visitDate=LocalDate.now().toString();dateButton.setText("Data visita: "+visitDate);specialtySpinner.setSelection(0);diagnosisSpinner.setSelection(0);prepare();}\n',
    activity,
    count=1,
)
if count != 1:
    raise SystemExit('R55 resetPreparation anchor not found')

# The grouping-window control must not survive anywhere in the special-tools page.
activity = activity.replace('windowSpinner=new Spinner(this);', '')
activity = activity.replace('windowSpinner.setSelection(9);', '')
activity = activity.replace('Finestra farmaci per il medico di base', '')

activity_path.write_text(activity, encoding='utf-8')

# Version identity for this corrective build.
gradle_path = Path('android-r3/app/build.gradle')
gradle = gradle_path.read_text(encoding='utf-8')
gradle = re.sub(r'versionCode\s+54\b', 'versionCode 55', gradle, count=1)
gradle = gradle.replace("versionName '1.0.0-android-r54-special-tools-ui-export-fix-test'", "versionName '1.0.0-android-r55-special-tools-layout-order-cleanup-test'")
gradle_path.write_text(gradle, encoding='utf-8')

# Align only inherited identity assertions after the intentional version bump.
for p in Path('android-r3/app/src/test').rglob('*.java'):
    s = p.read_text(encoding='utf-8')
    ns = s.replace('versionCode 54', 'versionCode 55').replace('versionCode = 54', 'versionCode = 55')
    ns = ns.replace('1.0.0-android-r54-special-tools-ui-export-fix-test', '1.0.0-android-r55-special-tools-layout-order-cleanup-test')
    if ns != s:
        p.write_text(ns, encoding='utf-8')

print('R55 special-tools layout/order cleanup applied')
