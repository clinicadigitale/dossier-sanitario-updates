from pathlib import Path
import re

BASE = Path('android-r3/app/src/main/java/it/dossiersanitario/clinicadigitale/beta')
TEST = Path('android-r3/app/src/test/java/it/dossiersanitario/clinicadigitale/beta')
MAIN = BASE / 'R6MainActivity.java'
CHART = BASE / 'R26ChartView.java'
GEOM = BASE / 'R47GraphGeometry.java'
CLOUD = BASE / 'R12CloudManager.java'
GRADLE = Path('android-r3/app/build.gradle')


def require(text, needle, label):
    if needle not in text:
        raise SystemExit('R51 missing ' + label)


def replace_block(text, signature, replacement, label):
    start = text.find(signature)
    if start < 0:
        raise SystemExit('R51 missing ' + label)
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
        raise SystemExit('R51 unclosed ' + label)
    return text[:start] + replacement.rstrip() + '\n' + text[end:]

# ---------------------------------------------------------------------------
# 1) GRAPH. R50/R47 data path stays frozen. Restore only useful vertical height
# and guarantee 5-6 readable year labels on ordinary multi-year series.
# ---------------------------------------------------------------------------
chart = CHART.read_text(encoding='utf-8')
chart, height_changes = re.subn(r'setMinimumHeight\(dp\(\d+\)\);', 'setMinimumHeight(dp(400));', chart, count=1)
if height_changes != 1:
    raise SystemExit('R51 could not identify the single R50 graph minimum height')
require(chart, 'float left = dp(66), right = getWidth() - dp(12), top = dp(20);', 'R50 graph geometry')
require(chart, 'R47GraphGeometry.yearStart(tMin)', 'R47 graph chronology')
require(chart, 'R47GraphGeometry.yearEndExclusive(tMax)', 'R47 graph chronology end')
CHART.write_text(chart, encoding='utf-8')

geom = GEOM.read_text(encoding='utf-8')
ticks = r'''    static int[] ticks(int firstYear, int lastYear, float plotWidthPx, float density) {
        if (lastYear < firstYear) return new int[0];
        int span = lastYear - firstYear;
        if (span == 0) return new int[]{firstYear};

        int desired = Math.min(6, span + 1);
        if (span >= 4) desired = Math.max(5, desired);
        List<Integer> list = new ArrayList<>();
        for (int i = 0; i < desired; i++) {
            int y = firstYear + (int)Math.round((span * i) / (double)(desired - 1));
            if (list.isEmpty() || list.get(list.size() - 1) != y) list.add(y);
        }
        if (list.get(0) != firstYear) list.add(0, firstYear);
        if (list.get(list.size() - 1) != lastYear) list.add(lastYear);
        int[] out = new int[list.size()];
        for (int i = 0; i < out.length; i++) out[i] = list.get(i);
        return out;
    }'''
geom = replace_block(geom, '    static int[] ticks(int firstYear, int lastYear, float plotWidthPx, float density) {', ticks, 'R47 tick selector')
GEOM.write_text(geom, encoding='utf-8')

# ---------------------------------------------------------------------------
# 2) LIGHTWEIGHT STARTUP CHECK. No automatic full sync, no sync-engine changes.
# Compare only the newest committed cloud snapshot name with the snapshot already
# reconciled locally. Network failures are silent and never block app startup.
# ---------------------------------------------------------------------------
cloud = CLOUD.read_text(encoding='utf-8')
insert_after = '''    public static boolean configured(SharedPreferences prefs) {\n        return loadConfig(prefs).optString("archiveId", "").length() > 0;\n    }\n'''
require(cloud, insert_after, 'configured method')
helper = r'''

    public static boolean r51HasNewerCloudData(Context context, SharedPreferences prefs) throws Exception {
        if (!configured(prefs) || syncing) return false;
        JSONObject cfg = loadConfig(prefs);
        SnapshotInfo latest = latestSnapshot(context, cfg);
        if (latest == null || latest.name == null || latest.name.trim().isEmpty()) return false;
        String local = cfg.optString("r36ReconciledSnapshotName", "");
        if (local.isEmpty()) local = cfg.optString("lastSnapshotName", "");
        return local.isEmpty() || !latest.name.equals(local);
    }
'''
cloud = cloud.replace(insert_after, insert_after + helper, 1)
CLOUD.write_text(cloud, encoding='utf-8')

main = MAIN.read_text(encoding='utf-8')
startup = '''        renderSection(initial);\n    }'''
require(main, startup, 'onCreate end')
main = main.replace(startup, '''        renderSection(initial);\n        r51CheckSyncReminderOnStartup();\n    }''', 1)

marker = '    @Override protected void onSaveInstanceState(Bundle outState) {'
require(main, marker, 'onSave insertion point')
methods = r'''    private void r51CheckSyncReminderOnStartup() {
        if (!R12CloudManager.configured(prefs)) return;
        long remindAfter = prefs.getLong("r51_sync_remind_after", 0L);
        if (System.currentTimeMillis() < remindAfter) return;
        new Thread(() -> {
            try {
                boolean newer = R12CloudManager.r51HasNewerCloudData(this, prefs);
                if (!newer || isFinishing()) return;
                runOnUiThread(() -> {
                    if (isFinishing()) return;
                    new AlertDialog.Builder(this)
                            .setTitle("Sincronizzazione dati sanitari")
                            .setMessage("I dati sanitari presenti su questo dispositivo non sono aggiornati. Vuoi sincronizzarli adesso?")
                            .setPositiveButton("Sincronizza ora", (d, w) -> R12CloudManager.syncInteractiveR31(this, prefs))
                            .setNegativeButton("Ricordamelo più tardi", (d, w) -> r51ChooseSyncSnooze())
                            .show();
                });
            } catch (Exception ignored) {
            }
        }, "clinica-r51-sync-check").start();
    }

    private void r51ChooseSyncSnooze() {
        final String[] labels = {"1 ora", "3 ore", "6 ore", "12 ore", "24 ore"};
        final long[] hours = {1L, 3L, 6L, 12L, 24L};
        new AlertDialog.Builder(this)
                .setTitle("Quando vuoi essere avvisato di nuovo?")
                .setItems(labels, (d, which) -> {
                    int i = Math.max(0, Math.min(hours.length - 1, which));
                    long until = System.currentTimeMillis() + hours[i] * 60L * 60L * 1000L;
                    prefs.edit().putLong("r51_sync_remind_after", until).apply();
                })
                .setNegativeButton("Annulla", null)
                .show();
    }

'''
main = main.replace(marker, methods + marker, 1)
MAIN.write_text(main, encoding='utf-8')

# Version only.
g = GRADLE.read_text(encoding='utf-8')
g = re.sub(r'versionCode\s*(?:=\s*)?\d+', 'versionCode 51', g, count=1)
g = re.sub(r'versionName\s*(?:=\s*)?[\"\'][^\"\']+[\"\']', 'versionName "1.0.0-android-r51-graph-height-ticks-sync-reminder-test"', g, count=1)
GRADLE.write_text(g, encoding='utf-8')

TEST.mkdir(parents=True, exist_ok=True)
(TEST / 'R51GraphHeightTicksSyncReminderTest.java').write_text(r'''package it.dossiersanitario.clinicadigitale.beta;

import static org.junit.Assert.*;
import org.junit.Test;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;

public class R51GraphHeightTicksSyncReminderTest {
    private String read(String p) throws Exception { return new String(Files.readAllBytes(Paths.get(p)), StandardCharsets.UTF_8); }

    @Test public void graphHeightRestoredWithoutChangingR47DataPath() throws Exception {
        String c = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R26ChartView.java");
        assertTrue(c.contains("setMinimumHeight(dp(400))"));
        assertTrue(c.contains("float left = dp(66), right = getWidth() - dp(12), top = dp(20);"));
        assertTrue(c.contains("R47GraphGeometry.yearStart(tMin)"));
        assertTrue(c.contains("R47GraphGeometry.yearEndExclusive(tMax)"));
    }

    @Test public void longRangeGetsSixTicksAndNeverOnlyThree() {
        int[] y = R47GraphGeometry.ticks(2003, 2026, 300f, 3f);
        assertEquals(6, y.length);
        assertEquals(2003, y[0]);
        assertEquals(2026, y[y.length - 1]);
    }

    @Test public void startupReminderUsesUnambiguousMedicalDataCopy() throws Exception {
        String m = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        assertTrue(m.contains("I dati sanitari presenti su questo dispositivo non sono aggiornati. Vuoi sincronizzarli adesso?"));
        assertTrue(m.contains("Sincronizza ora"));
        assertTrue(m.contains("Ricordamelo più tardi"));
        assertTrue(m.contains("syncInteractiveR31(this, prefs)"));
        assertTrue(m.contains("1 ora")); assertTrue(m.contains("3 ore")); assertTrue(m.contains("6 ore"));
        assertTrue(m.contains("12 ore")); assertTrue(m.contains("24 ore"));
        assertTrue(m.contains("r51_sync_remind_after"));
    }

    @Test public void startupCheckIsLightweightAndDoesNotAlterSyncEngine() throws Exception {
        String c = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R12CloudManager.java");
        assertTrue(c.contains("r51HasNewerCloudData"));
        assertTrue(c.contains("latestSnapshot(context, cfg)"));
        assertTrue(c.contains("r36ReconciledSnapshotName"));
        assertTrue(c.contains("lastSnapshotName"));
        assertTrue(c.contains("r50CopyVerified(partial, target)"));
        assertTrue(c.contains("r50CopyVerified(old, target)"));
    }
}
''', encoding='utf-8')

print('R51 graph height/ticks and lightweight startup sync reminder applied')
