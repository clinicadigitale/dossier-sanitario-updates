from pathlib import Path
import re

BASE = Path('android-r3/app/src/main/java/it/dossiersanitario/clinicadigitale/beta')
TEST = Path('android-r3/app/src/test/java/it/dossiersanitario/clinicadigitale/beta')
MAIN = BASE / 'R6MainActivity.java'
CHART = BASE / 'R26ChartView.java'
GRADLE = Path('android-r3/app/build.gradle')


def require(text, needle, label):
    if needle not in text:
        raise SystemExit('R52 missing ' + label)

# ---------------------------------------------------------------------------
# R52 SCOPE: graph height only. Keep R47/R50/R51 data, axes, sync and reminder
# logic untouched. Fix the REAL parent container height used by every graph.
# ---------------------------------------------------------------------------
main = MAIN.read_text(encoding='utf-8')
require(main, 'private void r27Chart', 'shared graph renderer')
require(main, 'new R33PressureChartView', 'pressure graph')
require(main, 'new R33WeightJourneyChartView', 'weight journey graph')

# Pure layout policy so portrait and landscape are independently testable.
layout = r'''package it.dossiersanitario.clinicadigitale.beta;

final class R52GraphLayout {
    static final int PORTRAIT_HEIGHT_DP = 430;
    static final int LANDSCAPE_HEIGHT_DP = 430;
    private R52GraphLayout() {}

    static int containerHeightDp(boolean landscape) {
        return landscape ? LANDSCAPE_HEIGHT_DP : PORTRAIT_HEIGHT_DP;
    }

    static int effectivePlotHeightDp(boolean landscape, boolean hasReference) {
        int reserve = hasReference ? 154 : 116;
        return containerHeightDp(landscape) - 20 - reserve;
    }
}
'''
(BASE / 'R52GraphLayout.java').write_text(layout, encoding='utf-8')

# Every graph in R6MainActivity is inserted through a variable called `chart`.
# Replace the actual fixed LayoutParams height, not only setMinimumHeight().
pattern = re.compile(
    r'([A-Za-z0-9_]+\.addView\(chart,\s*new LinearLayout\.LayoutParams\(ViewGroup\.LayoutParams\.MATCH_PARENT,\s*)dp\(\d+\)(\)\);)'
)
main, changed = pattern.subn(
    r'\1dp(R52GraphLayout.containerHeightDp(r36Landscape()))\2',
    main
)
if changed < 4:
    raise SystemExit('R52 expected at least 4 real graph containers, changed %d' % changed)

# No graph container may remain locked to a numeric dp height.
remaining = []
for line in main.splitlines():
    if '.addView(chart' in line and 'LinearLayout.LayoutParams' in line:
        if 'R52GraphLayout.containerHeightDp(r36Landscape())' not in line:
            remaining.append(line.strip())
if remaining:
    raise SystemExit('R52 graph containers not converted: ' + ' | '.join(remaining))

MAIN.write_text(main, encoding='utf-8')

# Keep the view minimum coherent with the real container. This does not alter
# data, axis, dates, labels, reference logic or rendering calculations.
chart = CHART.read_text(encoding='utf-8')
require(chart, 'setMinimumHeight(dp(400));', 'R51 minimum height')
chart = chart.replace('setMinimumHeight(dp(400));', 'setMinimumHeight(dp(430));', 1)
CHART.write_text(chart, encoding='utf-8')

# Version only.
g = GRADLE.read_text(encoding='utf-8')
g = re.sub(r'versionCode\s*(?:=\s*)?\d+', 'versionCode 52', g, count=1)
g = re.sub(r'versionName\s*(?:=\s*)?[\"\'][^\"\']+[\"\']', 'versionName "1.0.0-android-r52-all-graphs-height-test"', g, count=1)
GRADLE.write_text(g, encoding='utf-8')

# Regression tests: verify actual usable plot height in BOTH orientations and
# verify every graph route uses the shared real container-height policy.
TEST.mkdir(parents=True, exist_ok=True)
(TEST / 'R52AllGraphsPortraitLandscapeHeightTest.java').write_text(r'''package it.dossiersanitario.clinicadigitale.beta;

import static org.junit.Assert.*;
import org.junit.Test;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;

public class R52AllGraphsPortraitLandscapeHeightTest {
    private String read(String p) throws Exception {
        return new String(Files.readAllBytes(Paths.get(p)), StandardCharsets.UTF_8);
    }

    @Test public void portraitAndLandscapeHaveSameRealContainerHeight() {
        assertEquals(430, R52GraphLayout.containerHeightDp(false));
        assertEquals(430, R52GraphLayout.containerHeightDp(true));
    }

    @Test public void portraitAndLandscapeKeepLargeEffectivePlotArea() {
        assertTrue(R52GraphLayout.effectivePlotHeightDp(false, true) >= 250);
        assertTrue(R52GraphLayout.effectivePlotHeightDp(true, true) >= 250);
        assertEquals(R52GraphLayout.effectivePlotHeightDp(false, true),
                     R52GraphLayout.effectivePlotHeightDp(true, true));
    }

    @Test public void everyGraphContainerUsesOrientationAwareSharedHeight() throws Exception {
        String m = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        int chartViews = occurrences(m, "new R26ChartView(")
                + occurrences(m, "new R33PressureChartView(")
                + occurrences(m, "new R33WeightJourneyChartView(");
        int heightUses = occurrences(m, "dp(R52GraphLayout.containerHeightDp(r36Landscape()))");
        assertTrue("Expected all graph types to exist", chartViews >= 4);
        assertEquals("Every graph instance must use the R52 real height", chartViews, heightUses);
    }

    @Test public void r51DataAxisTicksReminderAndR50SyncStayFrozen() throws Exception {
        String c = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R26ChartView.java");
        String m = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R6MainActivity.java");
        String cloud = read("src/main/java/it/dossiersanitario/clinicadigitale/beta/R12CloudManager.java");
        assertTrue(c.contains("R47GraphGeometry.yearStart(tMin)"));
        assertTrue(c.contains("R47GraphGeometry.yearEndExclusive(tMax)"));
        assertTrue(c.contains("setMinimumHeight(dp(430))"));
        assertTrue(m.contains("I dati sanitari presenti su questo dispositivo non sono aggiornati. Vuoi sincronizzarli adesso?"));
        assertTrue(cloud.contains("r50CopyVerified(partial, target)"));
        assertTrue(cloud.contains("r50CopyVerified(old, target)"));
    }

    private int occurrences(String source, String needle) {
        int count = 0, at = 0;
        while ((at = source.indexOf(needle, at)) >= 0) { count++; at += needle.length(); }
        return count;
    }
}
''', encoding='utf-8')

print('R52 all graph containers: portrait 430dp, landscape 430dp; data/sync untouched; containers changed:', changed)
