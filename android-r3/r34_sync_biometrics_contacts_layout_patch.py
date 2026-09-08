from pathlib import Path

BASE = Path('android-r3/app/src/main/java/it/dossiersanitario/clinicadigitale/beta')
MAIN = BASE / 'R6MainActivity.java'
CLOUD = BASE / 'R12CloudManager.java'
MANIFEST = Path('android-r3/app/src/main/AndroidManifest.xml')
GRADLE = Path('android-r3/app/build.gradle')


def replace_block(text, signature, replacement, label=None):
    start = text.find(signature)
    if start < 0:
        raise SystemExit(f'R34 patch failed: missing {label or signature}')
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
        raise SystemExit(f'R34 patch failed: unclosed {label or signature}')
    return text[:start] + replacement.rstrip() + '\n' + text[end:]


def require(text, needle, label):
    if needle not in text:
        raise SystemExit(f'R34 patch failed: missing {label}')

# ---------------------------------------------------------------------------
# 1. Synchronization: fix the remaining ZipInputStream lifecycle bug and mirror
#    remote Windows changes into the exact R27/R30 disk-backed stores used by UI.
# ---------------------------------------------------------------------------
c = CLOUD.read_text(encoding='utf-8')
old_batch = 'out.add(parseEvent(readAll(zip), recovery))'
old_event = 'byte[] bytes = readAll(zip);'
require(c, old_batch, 'parseBatch closing read')
require(c, old_event, 'parseEvent closing read')
c = c.replace(old_batch, 'out.add(parseEvent(R25ZipEntryReader.readEntry(zip), recovery))', 1)
c = c.replace(old_event, 'byte[] bytes = R25ZipEntryReader.readEntry(zip);', 1)

# Mirror deletions to the exact Windows-compatible local arrays.
old_delete = 'if ("delete".equals(operation)) { removeRawEntity(prefs, store, entityId); removeNativeByWindowsId(prefs, store, entityId); if ("documents".equals(store)) markDocumentDeleted(prefs, entityId); return true; }'
new_delete = 'if ("delete".equals(operation)) { r34MirrorExactDelete(prefs, store, entityId); removeRawEntity(prefs, store, entityId); removeNativeByWindowsId(prefs, store, entityId); if ("documents".equals(store)) markDocumentDeleted(prefs, entityId); return true; }'
require(c, old_delete, 'remote delete block')
c = c.replace(old_delete, new_delete, 1)

old_save = '        saveRawEntity(prefs, store, entityId, entity);\n        if ("profiles".equals(store) && entityId.equals(cfg.optString("linkedProfileId"))) mapProfileToPrefs(prefs, entity);'
new_save = '        saveRawEntity(prefs, store, entityId, entity);\n        r34MirrorExactPut(prefs, cfg, store, entity);\n        if ("profiles".equals(store) && entityId.equals(cfg.optString("linkedProfileId"))) mapProfileToPrefs(prefs, entity);'
require(c, old_save, 'remote put block')
c = c.replace(old_save, new_save, 1)

insert_cloud = '    private static void applyDocumentEvent(Context context, SharedPreferences prefs, JSONObject cfg, JSONObject entity, Map<String, byte[]> files) throws Exception {'
require(c, insert_cloud, 'cloud mirror insertion point')
cloud_helpers = r'''    private static boolean r34ExactStore(String store) {
        return "doctors".equals(store)
                || "therapies".equals(store)
                || "exemptions".equals(store)
                || "diagnoses".equals(store)
                || "measurements".equals(store)
                || "weightJourneys".equals(store)
                || "documentVersions".equals(store)
                || "calendarEvents".equals(store)
                || "calendarSuggestions".equals(store);
    }

    private static void r34MirrorExactPut(SharedPreferences prefs, JSONObject cfg, String store, JSONObject entity) {
        if (prefs == null || entity == null || store == null) return;
        try {
            if ("profiles".equals(store) && entity.optString("id", "").equals(R27ExactWindows.activeProfileId(prefs))) {
                R27ExactWindows.updateActiveProfile(prefs, entity);
                return;
            }
            if (!r34ExactStore(store)) return;
            String profileId = entity.optString("profileId", "");
            String active = R27ExactWindows.activeProfileId(prefs);
            if (!profileId.isEmpty() && !active.isEmpty() && !profileId.equals(active)) return;
            R27ExactWindows.upsertData(prefs, store, entity);
        } catch (Throwable ignored) {}
    }

    private static void r34MirrorExactDelete(SharedPreferences prefs, String store, String entityId) {
        if (prefs == null || store == null || entityId == null || entityId.isEmpty()) return;
        try {
            if (r34ExactStore(store)) R27ExactWindows.deleteData(prefs, store, entityId);
        } catch (Throwable ignored) {}
    }

'''
c = c.replace(insert_cloud, cloud_helpers + insert_cloud, 1)
CLOUD.write_text(c, encoding='utf-8')

# ---------------------------------------------------------------------------
# 2. Android main UI: biometric/TOTP choice, clickable contacts and compact
#    landscape monitoring rows.
# ---------------------------------------------------------------------------
s = MAIN.read_text(encoding='utf-8')

# Second-factor preference keys.
const_marker = '    private static final String REMEMBER_PASSWORD_KEY = "r23_login_password_secure";\n'
require(s, const_marker, 'login constants')
s = s.replace(const_marker, const_marker +
'''    private static final String SECOND_FACTOR_METHOD_KEY = "r34_second_factor_method";\n'''
'''    private static final String SECOND_FACTOR_ASK = "ask";\n'''
'''    private static final String SECOND_FACTOR_BIOMETRIC = "biometric";\n'''
'''    private static final String SECOND_FACTOR_TOTP = "totp";\n''', 1)

# After password verification, do not force TOTP. Route through the chosen method.
old_mfa = r'''            if (account.optBoolean("mfaEnabled", false)) {
                String envelope = account.optString("mfaSecretEnvelope", "");
                if (envelope.trim().isEmpty()) {
                    Toast.makeText(this, "TOTP configurato ma non disponibile su questo dispositivo", Toast.LENGTH_LONG).show();
                    return;
                }
                String secret = R12Crypto.portableMfaUnprotect(envelope, password);
                showStartupTotp(state, secret);
                return;
            }
'''
new_mfa = r'''            if (account.optBoolean("mfaEnabled", false)) {
                r34ShowSecondFactor(state, account, password);
                return;
            }
'''
require(s, old_mfa, 'startup MFA branch')
s = s.replace(old_mfa, new_mfa, 1)

# TOTP dialog itself always exposes biometric as an alternative when available.
totp = r'''    private void showStartupTotp(Bundle state, String secret) {
        EditText otp = field("Codice TOTP a 6 cifre", "");
        otp.setInputType(android.text.InputType.TYPE_CLASS_NUMBER);
        AlertDialog.Builder builder = new AlertDialog.Builder(this)
                .setTitle("Seconda verifica · TOTP")
                .setMessage("Inserisci il codice TOTP oppure scegli la biometria del dispositivo.")
                .setView(otp)
                .setCancelable(false)
                .setNegativeButton("Esci", (d, w) -> finishAndRemoveTask())
                .setPositiveButton("Accedi", (d, w) -> {
                    if (!R12Crypto.verifyTotp(secret, clean(otp))) {
                        Toast.makeText(this, "Il codice TOTP non è valido", Toast.LENGTH_LONG).show();
                        showStartupTotp(state, secret);
                        return;
                    }
                    sessionAuthenticated = true;
                    showMainUi(state);
                });
        if (R34BiometricAuth.available(this)) {
            builder.setNeutralButton("Usa biometria", (d, w) -> r34AuthenticateBiometric(state, secret));
        }
        builder.show();
    }'''
s = replace_block(s, '    private void showStartupTotp(Bundle state, String secret) {', totp, 'TOTP dialog')

# Clickable mail and telephone values anywhere labelValue is used.
label_value = r'''    private LinearLayout labelValue(String label, String value) {
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setPadding(0, dp(5), 0, dp(5));
        row.addView(text(label, 13, MUTED, false), new LinearLayout.LayoutParams(dp(92), ViewGroup.LayoutParams.WRAP_CONTENT));
        TextView valueView = text(value, 13, TEXT, true);
        r34MakeContactAction(valueView, label, value);
        row.addView(valueView, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        return row;
    }'''
s = replace_block(s, '    private LinearLayout labelValue(String label, String value) {', label_value, 'labelValue')

# R33 generic monitoring detail becomes adaptive in landscape.
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
        boolean landscape=r34Landscape();
        for(JSONObject row:ordered){
            if(landscape){
                content.addView(r34MeasurementLandscapeRow(type,label,row),matchWrapBottom(7));
                continue;
            }
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
s = replace_block(s, '    private void r31RenderMonitorDetail(String type,String label){', monitor_detail, 'monitor detail')

# Weight history: all fields on one row in landscape, palette-aware thin separator between weigh-ins.
weight_history = r'''    private void r33RenderWeightHistory(JSONArray rows,boolean oldestFirst,JSONObject journey){
        java.util.ArrayList<JSONObject> chronological=r31SortedByDate(rows,true,"date","createdAt","updatedAt");
        String startDate=journey==null?"":journey.optString("startDate","");
        java.util.ArrayList<JSONObject> pertinent=new java.util.ArrayList<>();
        for(JSONObject row:chronological){String date=r31First(row,"date","createdAt");if(startDate.isEmpty()||date.isEmpty()||date.compareTo(startDate)>=0)pertinent.add(row);}
        java.util.ArrayList<JSONObject> display=new java.util.ArrayList<>(pertinent);if(!oldestFirst)java.util.Collections.reverse(display);
        LinearLayout history=card();history.addView(sectionHeader("Storico pesate"));
        if(display.isEmpty()){history.addView(text("Nessuna pesata pertinente al percorso.",13,MUTED,false));content.addView(history,matchWrapBottom(14));return;}
        double first=r33Number(pertinent.get(0),"value");
        boolean landscape=r34Landscape();
        for(int displayIndex=0;displayIndex<display.size();displayIndex++){
            JSONObject row=display.get(displayIndex);
            int original=pertinent.indexOf(row);double value=r33Number(row,"value");double previous=original>0?r33Number(pertinent.get(original-1),"value"):value;
            if(landscape){
                LinearLayout line=new LinearLayout(this);line.setOrientation(LinearLayout.HORIZONTAL);line.setGravity(Gravity.CENTER_VERTICAL);line.setPadding(0,dp(6),0,dp(6));
                r34AddInline(line,r31Display(row,"date","createdAt"),1.15f,true);
                r34AddInline(line,row.optString("time",""),0.75f,false);
                r34AddInline(line,R33WeightJourneyModel.fmt(value)+" kg",0.9f,true);
                r34AddInline(line,"Prec. "+r33Signed(value-previous)+" kg",1.05f,false);
                r34AddInline(line,"Inizio "+r33Signed(value-first)+" kg",1.05f,false);
                r34AddInline(line,row.optString("device",""),1.0f,false);
                r34AddInline(line,row.optString("notes",""),1.3f,false);
                Button edit=compactButton("Modifica");edit.setMinWidth(0);edit.setMinimumWidth(0);edit.setPadding(dp(8),0,dp(8),0);edit.setOnClickListener(v->r31EditMeasurement("weight",row));
                line.addView(edit,new LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT,dp(38)));
                history.addView(line);
            }else{
                LinearLayout line=new LinearLayout(this);line.setOrientation(LinearLayout.VERTICAL);line.setPadding(0,dp(7),0,dp(7));
                line.addView(text(r31Display(row,"date","createdAt")+"   "+R33WeightJourneyModel.fmt(value)+" kg",14,TEXT,true));
                line.addView(text("Diff. precedente "+r33Signed(value-previous)+" kg   ·   Diff. iniziale "+r33Signed(value-first)+" kg",12,MUTED,false));
                String note=row.optString("notes","");if(!note.isEmpty())line.addView(text(note,12,MUTED,false));
                Button edit=compactButton("Modifica");edit.setOnClickListener(v->r31EditMeasurement("weight",row));line.addView(edit,matchWrapTop(4));
                history.addView(line);
            }
            if(displayIndex<display.size()-1)history.addView(r34PaletteDivider());
        }
        content.addView(history,matchWrapBottom(14));
    }'''
s = replace_block(s, '    private void r33RenderWeightHistory(JSONArray rows,boolean oldestFirst,JSONObject journey){', weight_history, 'weight history')

# Add factor choice card to Preferences immediately before session timeout card.
pref_marker = '        LinearLayout session=card();session.addView(sectionHeader("Sicurezza della sessione"));'
require(s, pref_marker, 'preferences security marker')
pref_insert = r'''        LinearLayout verification=card();verification.addView(sectionHeader("Metodo di seconda verifica"));
        String factor=prefs.getString(SECOND_FACTOR_METHOD_KEY,SECOND_FACTOR_ASK);
        verification.addView(labelValue("Metodo preferito",r34SecondFactorLabel(factor)));
        verification.addView(labelValue("Biometria dispositivo",R34BiometricAuth.available(this)?"Disponibile":"Non disponibile / non configurata"));
        verification.addView(text("Puoi usare la biometria configurata sul telefono come alternativa al TOTP. Il TOTP resta disponibile quando configurato.",13,MUTED,false),matchWrapTop(6));
        Button changeFactor=button("Modifica metodo di verifica");changeFactor.setOnClickListener(v->r34ChoosePreferredSecondFactor());verification.addView(changeFactor,matchWrapTop(8));
        content.addView(verification,matchWrapBottom(14));

'''
s = s.replace(pref_marker, pref_insert + pref_marker, 1)

# Help text must not claim that TOTP alone is mandatory.
s = s.replace('Il secondo fattore diventa obbligatorio quando il Dossier viene associato a un cloud esterno.',
              'Quando è prevista una seconda verifica, su Android puoi usare la biometria configurata sul dispositivo oppure il TOTP.', 1)
s = s.replace('il proprio secondo fattore TOTP.', 'il metodo di seconda verifica scelto, biometria del dispositivo o TOTP.', 1)

# Helpers inserted before renderBackup after all R31/R33 helpers.
helper_point = '    private void renderBackup() {'
require(s, helper_point, 'R34 helper insertion point')
helpers = r'''    private void r34ShowSecondFactor(Bundle state, JSONObject account, String password) {
        String preferred = prefs.getString(SECOND_FACTOR_METHOD_KEY, SECOND_FACTOR_ASK);
        boolean biometric = R34BiometricAuth.available(this);
        boolean totp = account != null && !account.optString("mfaSecretEnvelope", "").trim().isEmpty();
        if (SECOND_FACTOR_BIOMETRIC.equals(preferred) && biometric) {
            r34AuthenticateBiometricForAccount(state, account, password);
            return;
        }
        if (SECOND_FACTOR_TOTP.equals(preferred) && totp) {
            r34ShowTotpForAccount(state, account, password);
            return;
        }
        if (!biometric && totp) {
            r34ShowTotpForAccount(state, account, password);
            return;
        }
        if (biometric && !totp) {
            r34AuthenticateBiometricForAccount(state, account, password);
            return;
        }
        if (!biometric) {
            Toast.makeText(this, "Nessun metodo di seconda verifica disponibile su questo dispositivo", Toast.LENGTH_LONG).show();
            return;
        }
        java.util.ArrayList<String> labels = new java.util.ArrayList<>();
        java.util.ArrayList<String> values = new java.util.ArrayList<>();
        labels.add("Biometria del dispositivo"); values.add(SECOND_FACTOR_BIOMETRIC);
        if (totp) { labels.add("Codice TOTP"); values.add(SECOND_FACTOR_TOTP); }
        new AlertDialog.Builder(this)
                .setTitle("Scegli il metodo di verifica")
                .setMessage("Puoi scegliere la biometria già configurata sul telefono oppure il codice TOTP.")
                .setItems(labels.toArray(new String[0]), (d, which) -> {
                    String selected = values.get(which);
                    if (SECOND_FACTOR_BIOMETRIC.equals(selected)) r34AuthenticateBiometricForAccount(state, account, password);
                    else r34ShowTotpForAccount(state, account, password);
                })
                .setNegativeButton("Esci", (d,w)->finishAndRemoveTask())
                .setCancelable(false)
                .show();
    }

    private void r34AuthenticateBiometricForAccount(Bundle state, JSONObject account, String password) {
        R34BiometricAuth.authenticate(this, new R34BiometricAuth.Callback() {
            @Override public void onAuthenticated() {
                sessionAuthenticated = true;
                showMainUi(state);
            }
            @Override public void onUseTotp() {
                r34ShowTotpForAccount(state, account, password);
            }
        });
    }

    private void r34AuthenticateBiometric(Bundle state, String secret) {
        R34BiometricAuth.authenticate(this, new R34BiometricAuth.Callback() {
            @Override public void onAuthenticated() {
                sessionAuthenticated = true;
                showMainUi(state);
            }
            @Override public void onUseTotp() { showStartupTotp(state, secret); }
        });
    }

    private void r34ShowTotpForAccount(Bundle state, JSONObject account, String password) {
        try {
            String envelope = account == null ? "" : account.optString("mfaSecretEnvelope", "");
            if (envelope.trim().isEmpty()) {
                Toast.makeText(this, "TOTP non configurato per questo account", Toast.LENGTH_LONG).show();
                if (R34BiometricAuth.available(this)) r34AuthenticateBiometricForAccount(state, account, password);
                return;
            }
            String secret = R12Crypto.portableMfaUnprotect(envelope, password);
            showStartupTotp(state, secret);
        } catch (Exception e) {
            Toast.makeText(this, "TOTP non disponibile su questo dispositivo", Toast.LENGTH_LONG).show();
            if (R34BiometricAuth.available(this)) r34AuthenticateBiometricForAccount(state, account, password);
        }
    }

    private void r34ChoosePreferredSecondFactor() {
        boolean biometric = R34BiometricAuth.available(this);
        java.util.ArrayList<String> labels = new java.util.ArrayList<>();
        java.util.ArrayList<String> values = new java.util.ArrayList<>();
        labels.add("Chiedi ogni volta"); values.add(SECOND_FACTOR_ASK);
        if (biometric) { labels.add("Biometria del dispositivo"); values.add(SECOND_FACTOR_BIOMETRIC); }
        labels.add("Codice TOTP"); values.add(SECOND_FACTOR_TOTP);
        new AlertDialog.Builder(this)
                .setTitle("Metodo di seconda verifica")
                .setItems(labels.toArray(new String[0]), (d, which) -> {
                    prefs.edit().putString(SECOND_FACTOR_METHOD_KEY, values.get(which)).apply();
                    Toast.makeText(this, "Metodo di verifica aggiornato", Toast.LENGTH_SHORT).show();
                    renderSection("Preferenze");
                })
                .setNegativeButton("Annulla", null)
                .show();
    }

    private String r34SecondFactorLabel(String value) {
        if (SECOND_FACTOR_BIOMETRIC.equals(value)) return "Biometria del dispositivo";
        if (SECOND_FACTOR_TOTP.equals(value)) return "Codice TOTP";
        return "Chiedi ogni volta";
    }

    private void r34MakeContactAction(TextView view, String label, String value) {
        if (view == null || value == null || value.trim().isEmpty()) return;
        String lower = label == null ? "" : label.toLowerCase(Locale.ROOT);
        boolean email = lower.contains("mail") || lower.contains("e-mail");
        boolean phone = lower.contains("telefono") || lower.contains("cellulare") || lower.equals("tel") || lower.startsWith("tel.");
        if (!email && !phone) return;
        view.setTextColor(R27ExactWindows.activeProfileColor(prefs, GREEN));
        view.setPaintFlags(view.getPaintFlags() | android.graphics.Paint.UNDERLINE_TEXT_FLAG);
        view.setClickable(true);
        view.setFocusable(true);
        if (email) {
            view.setContentDescription("Invia e-mail a " + value);
            view.setOnClickListener(v -> {
                try { startActivity(new Intent(Intent.ACTION_SENDTO, Uri.parse("mailto:" + Uri.encode(value.trim())))); }
                catch (Exception e) { Toast.makeText(this, "Nessuna app di posta disponibile", Toast.LENGTH_LONG).show(); }
            });
        } else {
            view.setContentDescription("Chiama " + value);
            view.setOnClickListener(v -> {
                try { startActivity(new Intent(Intent.ACTION_DIAL, Uri.parse("tel:" + Uri.encode(value.trim())))); }
                catch (Exception e) { Toast.makeText(this, "Nessuna app telefono disponibile", Toast.LENGTH_LONG).show(); }
            });
        }
    }

    private boolean r34Landscape() {
        return getResources().getConfiguration().orientation == Configuration.ORIENTATION_LANDSCAPE;
    }

    private View r34PaletteDivider() {
        View divider = new View(this);
        int base = R27ExactWindows.globalThemeColor(prefs, GREEN);
        divider.setBackgroundColor(Color.argb(105, Color.red(base), Color.green(base), Color.blue(base)));
        divider.setLayoutParams(new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(1)));
        return divider;
    }

    private void r34AddInline(LinearLayout row, String value, float weight, boolean bold) {
        TextView v = text(value == null || value.trim().isEmpty() ? "—" : value.trim(), 12, bold ? TEXT : MUTED, bold);
        v.setSingleLine(true);
        v.setEllipsize(android.text.TextUtils.TruncateAt.END);
        v.setPadding(dp(4),0,dp(4),0);
        row.addView(v, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, weight));
    }

    private LinearLayout r34MeasurementLandscapeRow(String type, String label, JSONObject row) {
        LinearLayout card = card();
        card.setPadding(dp(12),dp(8),dp(12),dp(8));
        if ("blood_pressure".equals(type)) {
            LinearLayout first = new LinearLayout(this); first.setOrientation(LinearLayout.HORIZONTAL); first.setGravity(Gravity.CENTER_VERTICAL);
            r34AddInline(first, r31First(row,"date","createdAt"), 1.0f, true);
            r34AddInline(first, row.optString("time",""), 0.7f, false);
            r34AddInline(first, row.optString("device",""), 1.5f, false);
            card.addView(first);
            LinearLayout second = new LinearLayout(this); second.setOrientation(LinearLayout.HORIZONTAL); second.setGravity(Gravity.CENTER_VERTICAL); second.setPadding(0,dp(3),0,0);
            r34AddInline(second, "Sistolica  "+row.optString("systolic","")+" mmHg", 1.25f, true);
            r34AddInline(second, "Diastolica  "+row.optString("diastolic","")+" mmHg", 1.25f, true);
            r34AddInline(second, "Frequenza  "+row.optString("heartRate","")+" bpm", 1.25f, false);
            Button edit=compactButton("Modifica");edit.setMinWidth(0);edit.setMinimumWidth(0);edit.setPadding(dp(8),0,dp(8),0);edit.setOnClickListener(v->r31EditMeasurement(type,row));
            second.addView(edit,new LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT,dp(38)));
            card.addView(second);
            return card;
        }
        LinearLayout first = new LinearLayout(this); first.setOrientation(LinearLayout.HORIZONTAL); first.setGravity(Gravity.CENTER_VERTICAL);
        String actual=row.optString("type",type);String rowLabel="body".equals(type)?r31BodyLabel(actual):label;
        r34AddInline(first,r31First(row,"date","createdAt"),1.0f,true);
        r34AddInline(first,row.optString("time",""),0.65f,false);
        r34AddInline(first,rowLabel,1.25f,true);
        String value=row.optString("value","")+(row.optString("unit","").isEmpty()?"":" "+row.optString("unit",""));
        r34AddInline(first,value,0.9f,true);
        r34AddInline(first,row.optString("device",""),1.1f,false);
        Button edit=compactButton("Modifica");edit.setMinWidth(0);edit.setMinimumWidth(0);edit.setPadding(dp(8),0,dp(8),0);edit.setOnClickListener(v->r31EditMeasurement(actual,row));
        first.addView(edit,new LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT,dp(38)));
        card.addView(first);
        String context=row.optString("context","");String notes=row.optString("notes","");
        if(!context.isEmpty()||!notes.isEmpty()){
            LinearLayout second=new LinearLayout(this);second.setOrientation(LinearLayout.HORIZONTAL);second.setPadding(0,dp(3),0,0);
            r34AddInline(second,context,1.0f,false);r34AddInline(second,notes,2.0f,false);card.addView(second);
        }
        return card;
    }

'''
s = s.replace(helper_point, helpers + helper_point, 1)

# Version labels.
s = s.replace('Android R33 TEST COMPLETO', 'Android R34 TEST COMPLETO')
s = s.replace('Aiuto R33', 'Aiuto R34')
MAIN.write_text(s, encoding='utf-8')

# ---------------------------------------------------------------------------
# 3. Manifest + version.
# ---------------------------------------------------------------------------
m = MANIFEST.read_text(encoding='utf-8')
perm = '    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />\n'
require(m, perm, 'manifest network permission')
if 'android.permission.USE_BIOMETRIC' not in m:
    m = m.replace(perm, perm + '    <uses-permission android:name="android.permission.USE_BIOMETRIC" />\n', 1)
MANIFEST.write_text(m, encoding='utf-8')

g = GRADLE.read_text(encoding='utf-8')
require(g, 'versionCode 33', 'versionCode 33')
require(g, "versionName '1.0.0-android-r33-clinical-weight-parity-test'", 'R33 versionName')
g = g.replace('versionCode 33', 'versionCode 34', 1)
g = g.replace("versionName '1.0.0-android-r33-clinical-weight-parity-test'", "versionName '1.0.0-android-r34-sync-biometrics-contacts-layout-test'", 1)
GRADLE.write_text(g, encoding='utf-8')

print('R34 sync, biometrics, clickable contacts and landscape monitoring patch applied')
