from pathlib import Path

MAIN = Path('android-r3/app/src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java')
GRADLE = Path('android-r3/app/build.gradle')

s = MAIN.read_text(encoding='utf-8')
marker = '    private void renderBackup() {'
if marker not in s:
    raise SystemExit('R27 preferences patch failed: backup marker missing')

method = r'''    private void renderPreferenze() {
        JSONObject global = R27ExactWindows.globalPreferences(prefs);
        JSONObject profile = R27ExactWindows.profilePreferences(prefs);

        LinearLayout c = card();
        c.addView(sectionHeader("Preferenze importate da Windows"));
        c.addView(labelValue("Palette programma", global.optString("palette", "teal")));
        c.addView(labelValue("Tema", global.optString("theme", "light")));
        c.addView(labelValue("Dimensione testo", global.optString("textScale", "normal")));
        c.addView(labelValue("Densità", global.optString("density", "comfortable")));
        c.addView(labelValue("Frequenza backup", global.optString("backupFrequency", "weekly")));
        c.addView(labelValue("Conferma importazioni", String.valueOf(global.optBoolean("confirmImports", true))));
        c.addView(labelValue("Giorni raggruppamento riordino farmaci", String.valueOf(global.optInt("medicationReorderGroupDays", 7))));
        c.addView(labelValue("E-mail Google Calendar", global.optString("googleCalendarEmail", "")));
        JSONArray reminders = global.optJSONArray("agendaDefaultReminders");
        if (reminders != null) c.addView(labelValue("Avvisi Agenda predefiniti", reminders.toString()));
        content.addView(c, matchWrapBottom(14));

        LinearLayout pc = card();
        pc.addView(sectionHeader("Preferenze del profilo attivo"));
        TextView swatch = text("Colore profilo Windows", 14, Color.WHITE, true);
        swatch.setPadding(dp(12), dp(12), dp(12), dp(12));
        swatch.setBackgroundColor(R27ExactWindows.activeProfileColor(prefs, GREEN));
        pc.addView(swatch, matchWrapTop(7));
        java.util.Iterator<String> keys = profile.keys();
        int shown = 0;
        while (keys.hasNext() && shown < 50) {
            String key = keys.next();
            Object value = profile.opt(key);
            if (value instanceof JSONObject) continue;
            pc.addView(labelValue(key, String.valueOf(value)));
            shown++;
        }
        content.addView(pc, matchWrapBottom(14));

        LinearLayout profilesCard = card();
        profilesCard.addView(sectionHeader("Profili disponibili e colori"));
        JSONArray profiles = R27ExactWindows.profiles(prefs);
        String active = R27ExactWindows.activeProfileId(prefs);
        for (int i = 0; i < profiles.length(); i++) {
            JSONObject p = profiles.optJSONObject(i);
            if (p == null) continue;
            JSONObject pp = p.optJSONObject("preferences");
            int color = GREEN;
            try {
                String hex = pp == null ? "" : pp.optString("profileColor", "");
                if (hex.matches("#[0-9A-Fa-f]{6}")) color = Color.parseColor(hex);
            } catch (Exception ignored) {}
            TextView row = text((active.equals(p.optString("id", "")) ? "✓ " : "") + r27ProfileName(p), 13, Color.WHITE, true);
            row.setPadding(dp(10), dp(9), dp(10), dp(9));
            row.setBackgroundColor(color);
            final String pid = p.optString("id", "");
            row.setOnClickListener(v -> {
                R27ExactWindows.setActiveProfile(prefs, pid);
                loadR26ImportedUiSettings();
                showMainUi(null);
                renderSection("Preferenze");
            });
            profilesCard.addView(row, matchWrapTop(6));
        }
        Button switcher = button("Cambia profilo");
        switcher.setOnClickListener(v -> showR27ProfilePicker());
        profilesCard.addView(switcher, matchWrapTop(10));
        content.addView(profilesCard, matchWrapBottom(14));

        JSONArray users = R27ExactWindows.users(prefs);
        LinearLayout uc = card();
        uc.addView(sectionHeader("Account importati dal Dossier Windows"));
        uc.addView(labelValue("Account", String.valueOf(users.length())));
        for (int i = 0; i < users.length(); i++) {
            JSONObject u = users.optJSONObject(i);
            if (u == null) continue;
            String name = u.optString("displayName", u.optString("username", "Utente"));
            String role = u.optString("role", u.optString("accessLevel", ""));
            uc.addView(text(name + (role.isEmpty() ? "" : " · " + role), 13, TEXT, false));
        }
        content.addView(uc, matchWrapBottom(14));
    }

'''
s = s.replace(marker, method + marker, 1)
s = s.replace('Android R26 QUASI DEFINITIVA', 'Android R27 TEST COMPLETO')
s = s.replace('Aiuto R26', 'Aiuto R27')
s = s.replace('R26: sezione collegata al Dossier sincronizzato', 'R27: sezione completa collegata al backup Windows')
s = s.replace('R26 mantiene lo stesso pacchetto Android', 'R27 mantiene lo stesso pacchetto Android')
s = s.replace('Installala sopra la R25', 'Installala sopra la R26')
MAIN.write_text(s, encoding='utf-8')

g = GRADLE.read_text(encoding='utf-8')
if 'versionCode 26' not in g or "versionName '1.0.0-android-r26-near-final'" not in g:
    raise SystemExit('R27 version patch failed')
g = g.replace('versionCode 26', 'versionCode 27', 1)
g = g.replace("versionName '1.0.0-android-r26-near-final'", "versionName '1.0.0-android-r27-complete-test'", 1)
GRADLE.write_text(g, encoding='utf-8')
print('R27 preferences and version patch applied')
