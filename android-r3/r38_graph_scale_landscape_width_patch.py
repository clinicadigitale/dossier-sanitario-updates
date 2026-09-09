from pathlib import Path

BASE = Path('android-r3/app/src/main/java/it/dossiersanitario/clinicadigitale/beta')
MAIN = BASE / 'R6MainActivity.java'
CHART = BASE / 'R26ChartView.java'
GRADLE = Path('android-r3/app/build.gradle')


def require(text, needle, label):
    if needle not in text:
        raise SystemExit(f'R38 patch failed: missing {label}')


def replace_block(text, signature, replacement, label=None):
    start = text.find(signature)
    if start < 0:
        raise SystemExit(f'R38 patch failed: missing {label or signature}')
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
        raise SystemExit(f'R38 patch failed: unclosed {label or signature}')
    return text[:start] + replacement.rstrip() + '\n' + text[end:]


# ---------------------------------------------------------------------------
# 1. Generic clinical chart: use the requested data field only, parse numbers
#    with units/decimal commas robustly, and scale the Y axis to the REAL range.
#    The old fixed 0.5 margin could visually flatten small but real variations.
# ---------------------------------------------------------------------------
chart = r'''package it.dossiersanitario.clinicadigitale.beta;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Path;
import android.view.View;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Locale;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/** R38 clinical line chart: strict requested-field data + real-range vertical scaling. */
final class R26ChartView extends View {
    private static final Pattern NUMBER = Pattern.compile("[-+]?\\d+(?:[\\.,]\\d+)?");
    private final Paint grid = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint line = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint point = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint label = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final List<Double> values = new ArrayList<>();
    private String emptyText = "Nessun dato numerico disponibile";
    private double dataMin = Double.NaN;
    private double dataMax = Double.NaN;

    R26ChartView(Context context, JSONArray records, int accent, String... preferredKeys) {
        super(context);
        setMinimumHeight(dp(260));
        grid.setColor(Color.rgb(224, 232, 229));
        grid.setStrokeWidth(dp(1));
        line.setColor(accent);
        line.setStrokeWidth(dp(3));
        line.setStyle(Paint.Style.STROKE);
        point.setColor(accent);
        point.setStyle(Paint.Style.FILL);
        label.setColor(Color.rgb(91, 105, 101));
        label.setTextSize(dp(11));
        if (records != null) {
            for (int i = 0; i < records.length(); i++) {
                JSONObject o = records.optJSONObject(i);
                double v = requestedValue(o, preferredKeys);
                if (!Double.isNaN(v) && !Double.isInfinite(v)) values.add(v);
            }
        }
        if (!values.isEmpty()) {
            dataMin = Collections.min(values);
            dataMax = Collections.max(values);
        }
    }

    static double requestedValue(JSONObject o, String... preferredKeys) {
        if (o == null || preferredKeys == null || preferredKeys.length == 0) return Double.NaN;
        for (String key : preferredKeys) {
            if (key == null || key.trim().isEmpty() || !o.has(key)) continue;
            Object raw = o.opt(key);
            if (raw instanceof Number) return ((Number) raw).doubleValue();
            if (raw == null || raw == JSONObject.NULL) continue;
            Matcher matcher = NUMBER.matcher(String.valueOf(raw).trim());
            if (!matcher.find()) continue;
            try { return Double.parseDouble(matcher.group().replace(',', '.')); }
            catch (Exception ignored) {}
        }
        return Double.NaN;
    }

    static double[] scaledBounds(double min, double max) {
        if (!Double.isFinite(min) || !Double.isFinite(max)) return new double[]{0.0, 1.0};
        if (max < min) { double t = min; min = max; max = t; }
        double span = max - min;
        if (span < 0.0000001) {
            double pad = Math.max(1.0, Math.abs(max) * 0.02);
            return new double[]{min - pad, max + pad};
        }
        double pad = Math.max(span * 0.12, 0.02);
        return new double[]{min - pad, max + pad};
    }

    void setEmptyText(String value) {
        if (value != null && !value.trim().isEmpty()) emptyText = value;
    }

    boolean hasData() { return !values.isEmpty(); }
    int dataCount() { return values.size(); }
    double dataMin() { return dataMin; }
    double dataMax() { return dataMax; }
    List<Double> dataValues() { return new ArrayList<>(values); }

    @Override protected void onDraw(Canvas canvas) {
        super.onDraw(canvas);
        float left = dp(52), right = getWidth() - dp(16), top = dp(18), bottom = getHeight() - dp(38);
        if (right <= left || bottom <= top) return;
        if (values.isEmpty()) {
            canvas.drawText(emptyText, left, top + dp(28), label);
            return;
        }

        double[] bounds = scaledBounds(dataMin, dataMax);
        double min = bounds[0], max = bounds[1];
        for (int i = 0; i <= 4; i++) {
            float y = top + (bottom - top) * i / 4f;
            canvas.drawLine(left, y, right, y, grid);
            double tick = max - (max - min) * i / 4.0;
            canvas.drawText(shortNumber(tick), dp(4), y + dp(4), label);
        }

        Path p = new Path();
        for (int i = 0; i < values.size(); i++) {
            float x = values.size() == 1 ? (left + right) / 2f : left + (right - left) * i / (values.size() - 1f);
            float y = bottom - (float) ((values.get(i) - min) / (max - min)) * (bottom - top);
            if (i == 0) p.moveTo(x, y); else p.lineTo(x, y);
            canvas.drawCircle(x, y, dp(4.0f), point);
        }
        if (values.size() > 1) canvas.drawPath(p, line);
        canvas.drawText(values.size() + " rilevazioni · min " + shortNumber(dataMin) + " · max " + shortNumber(dataMax), left, getHeight() - dp(8), label);
    }

    private String shortNumber(double v) {
        if (Math.abs(v - Math.rint(v)) < 0.005) return String.valueOf((long) Math.rint(v));
        return String.format(Locale.ITALY, "%.2f", v).replaceAll("0+$", "").replaceAll("[,.]$", "");
    }

    private int dp(float value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }
}
'''
CHART.write_text(chart, encoding='utf-8')

# ---------------------------------------------------------------------------
# 2. Landscape first label column: R37's cap was still too narrow on the real
#    Xiaomi. Portrait remains exactly frozen at 92 dp.
# ---------------------------------------------------------------------------
s = MAIN.read_text(encoding='utf-8')
label_value = r'''    private LinearLayout labelValue(String label, String value) {
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setPadding(0, dp(5), 0, dp(5));

        boolean landscape = r36Landscape();
        int labelWidth;
        TextView labelView = text(label, 13, MUTED, false);
        if (landscape) {
            int screenWidth = getResources().getDisplayMetrics().widthPixels;
            labelWidth = Math.max(dp(340), Math.min(dp(420), Math.round(screenWidth * 0.50f)));
            labelView.setSingleLine(true);
        } else {
            labelWidth = dp(92);
        }
        row.addView(labelView, new LinearLayout.LayoutParams(labelWidth, ViewGroup.LayoutParams.WRAP_CONTENT));

        String visibleValue = r36HumanReminderDisplay(label, value);
        TextView valueView = text(visibleValue, 13, TEXT, true);
        r34MakeContactAction(valueView, label, value);
        row.addView(valueView, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        return row;
    }'''
s = replace_block(s, '    private LinearLayout labelValue(String label, String value) {', label_value, 'landscape first column')

# Give charts more vertical room, especially with the phone rotated.
old_chart = '        c.addView(chart, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(230)));'
require(s, old_chart, 'r27 chart height')
s = s.replace(old_chart, '        c.addView(chart, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, r36Landscape() ? dp(330) : dp(280)));', 1)

# Also widen the first fields in compact monitoring rows so landscape does not
# regress to the cramped R34 proportions.
s = s.replace('r34AddInline(first, r31First(row,"date","createdAt"), 1.0f, true);',
              'r34AddInline(first, r31First(row,"date","createdAt"), 1.45f, true);', 2)
s = s.replace('r34AddInline(first, row.optString("time",""), 0.7f, false);',
              'r34AddInline(first, row.optString("time",""), 0.9f, false);', 1)
s = s.replace('r34AddInline(first,row.optString("time",""),0.65f,false);',
              'r34AddInline(first,row.optString("time",""),0.85f,false);', 1)

# Weight history date/time fields likewise stay readable in landscape.
s = s.replace('r34AddInline(line,r31Display(row,"date","createdAt"),1.15f,true);',
              'r34AddInline(line,r31Display(row,"date","createdAt"),1.55f,true);', 1)
s = s.replace('r34AddInline(line,row.optString("time",""),0.75f,false);',
              'r34AddInline(line,row.optString("time",""),0.95f,false);', 1)

require(s, 'Android R37 TEST COMPLETO', 'R37 release marker')
s = s.replace('Android R37 TEST COMPLETO', 'Android R38 TEST COMPLETO', 1)
MAIN.write_text(s, encoding='utf-8')

# ---------------------------------------------------------------------------
# 3. Version only. No other working sector is touched.
# ---------------------------------------------------------------------------
g = GRADLE.read_text(encoding='utf-8')
require(g, 'versionCode 37', 'versionCode 37')
require(g, "versionName '1.0.0-android-r37-frozen-portrait-landscape-graphs-agenda-test'", 'R37 versionName')
g = g.replace('versionCode 37', 'versionCode 38', 1)
g = g.replace("versionName '1.0.0-android-r37-frozen-portrait-landscape-graphs-agenda-test'",
              "versionName '1.0.0-android-r38-graph-scale-landscape-width-test'", 1)
GRADLE.write_text(g, encoding='utf-8')

print('R38 real-range graph scaling and wider landscape first-column patch applied')
