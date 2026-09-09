from pathlib import Path

BASE = Path('android-r3/app/src/main/java/it/dossiersanitario/clinicadigitale/beta')
MAIN = BASE / 'R6MainActivity.java'
CHART = BASE / 'R26ChartView.java'
CLOUD = BASE / 'R12CloudManager.java'
GRADLE = Path('android-r3/app/build.gradle')


def replace_block(text, signature, replacement, label=None):
    start = text.find(signature)
    if start < 0:
        raise SystemExit(f'R41 failed: missing {label or signature}')
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
        raise SystemExit(f'R41 failed: unclosed {label or signature}')
    return text[:start] + replacement.rstrip() + '\n' + text[end:]


# 1) GLOBAL LANDSCAPE POLICY FOR EVERY STANDARD LABEL/VALUE ROW.
# Portrait stays exactly at the historical 92dp first column.
s = MAIN.read_text(encoding='utf-8')
label_value = r'''    private LinearLayout labelValue(String label, String value) {
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setPadding(0, dp(5), 0, dp(5));

        boolean landscape = r36Landscape();
        TextView labelView = text(label, 13, MUTED, false);
        String visibleValue = r36HumanReminderDisplay(label, value);
        TextView valueView = text(visibleValue, 13, TEXT, true);
        r34MakeContactAction(valueView, label, value);

        if (landscape) {
            labelView.setSingleLine(true);
            labelView.setMaxLines(1);
            labelView.setHorizontallyScrolling(false);
            labelView.setEllipsize(null);
            row.addView(labelView, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 0.48f));
            row.addView(valueView, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 0.52f));
        } else {
            row.addView(labelView, new LinearLayout.LayoutParams(dp(92), ViewGroup.LayoutParams.WRAP_CONTENT));
            row.addView(valueView, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        }
        return row;
    }'''
s = replace_block(s, '    private LinearLayout labelValue(String label, String value) {', label_value, 'global labelValue')
s = s.replace('Android R40 TEST COMPLETO', 'Android R41 TEST COMPLETO', 1)
MAIN.write_text(s, encoding='utf-8')


# 2) WINDOWS-LIKE CLINICAL CHARTS.
# Uses the exact imported series, derives the latest usable report reference range,
# includes it in Y scaling, draws dashed reference lines, unit axis, clinical-date axis,
# and a reference legend. No external medical ranges are invented.
chart = r'''package it.dossiersanitario.clinicadigitale.beta;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.DashPathEffect;
import android.graphics.Paint;
import android.graphics.Path;
import android.view.View;

import org.json.JSONArray;
import org.json.JSONObject;

import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Date;
import java.util.List;
import java.util.Locale;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/** R41 clinical line chart: Windows-backed data, report reference lines and date-axis parity. */
final class R26ChartView extends View {
    private static final Pattern NUMBER = Pattern.compile("[-+]?\\d+(?:[\\.,]\\d+)?");
    private static final Pattern RANGE = Pattern.compile("([-+]?\\d+(?:[\\.,]\\d+)?)\\s*(?:-|–|—|a|to)\\s*([-+]?\\d+(?:[\\.,]\\d+)?)", Pattern.CASE_INSENSITIVE);
    private final Paint grid = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint line = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint point = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint label = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint reference = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final List<Double> values = new ArrayList<>();
    private final List<String> dates = new ArrayList<>();
    private String emptyText = "Nessun dato numerico disponibile";
    private double dataMin = Double.NaN;
    private double dataMax = Double.NaN;
    private double referenceLow = Double.NaN;
    private double referenceHigh = Double.NaN;
    private String referenceUnit = "";
    private String referenceDate = "";

    R26ChartView(Context context, JSONArray records, int accent, String... preferredKeys) {
        super(context);
        setMinimumHeight(dp(300));
        grid.setColor(Color.rgb(224, 232, 229));
        grid.setStrokeWidth(dp(1));
        line.setColor(accent);
        line.setStrokeWidth(dp(3));
        line.setStyle(Paint.Style.STROKE);
        point.setColor(accent);
        point.setStyle(Paint.Style.FILL);
        label.setColor(Color.rgb(91, 105, 101));
        label.setTextSize(dp(11));
        reference.setColor(accent);
        reference.setStyle(Paint.Style.STROKE);
        reference.setStrokeWidth(dp(2));
        reference.setPathEffect(new DashPathEffect(new float[]{dp(8), dp(6)}, 0));

        if (records != null) {
            for (int i = 0; i < records.length(); i++) {
                JSONObject o = records.optJSONObject(i);
                double v = requestedValue(o, preferredKeys);
                if (!Double.isNaN(v) && !Double.isInfinite(v)) {
                    values.add(v);
                    dates.add(o == null ? "" : firstText(o, "date", "clinicalDate", "issueDate", "createdAt"));
                }
                scanReference(o);
            }
        }
        if (!values.isEmpty()) {
            dataMin = Collections.min(values);
            dataMax = Collections.max(values);
        }
    }

    static double parseRequestedRaw(Object raw) {
        if (raw == null || raw == JSONObject.NULL) return Double.NaN;
        if (raw instanceof Number) return ((Number) raw).doubleValue();
        Matcher matcher = NUMBER.matcher(String.valueOf(raw).trim());
        if (!matcher.find()) return Double.NaN;
        try { return Double.parseDouble(matcher.group().replace(',', '.')); }
        catch (Exception ignored) { return Double.NaN; }
    }

    static double requestedValue(JSONObject o, String... preferredKeys) {
        if (o == null || preferredKeys == null || preferredKeys.length == 0) return Double.NaN;
        for (String key : preferredKeys) {
            if (key == null || key.trim().isEmpty() || !o.has(key)) continue;
            double parsed = parseRequestedRaw(o.opt(key));
            if (!Double.isNaN(parsed)) return parsed;
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

    static double[] scaledBoundsWithReference(double min, double max, double refLow, double refHigh) {
        if (!Double.isFinite(refLow) || !Double.isFinite(refHigh)) return scaledBounds(min, max);
        double low = Math.min(min, Math.min(refLow, refHigh));
        double high = Math.max(max, Math.max(refLow, refHigh));
        if (!Double.isFinite(low) || !Double.isFinite(high)) return scaledBounds(min, max);
        double span = high - low;
        if (span < 0.0000001) return scaledBounds(low, high);
        double pad = Math.max(span * 0.18, 0.02);
        return new double[]{low - pad, high + pad};
    }

    private void scanReference(JSONObject row) {
        if (row == null) return;
        double low = firstNumber(row,
                "referenceLow", "referenceMin", "refLow", "refMin", "rangeLow", "rangeMin",
                "lowerReference", "minReference", "referenceLower", "valoreMinimoRiferimento", "riferimentoMin");
        double high = firstNumber(row,
                "referenceHigh", "referenceMax", "refHigh", "refMax", "rangeHigh", "rangeMax",
                "upperReference", "maxReference", "referenceUpper", "valoreMassimoRiferimento", "riferimentoMax");

        Object referenceObject = row.opt("reference");
        if ((!Double.isFinite(low) || !Double.isFinite(high)) && referenceObject instanceof JSONObject) {
            JSONObject ro = (JSONObject) referenceObject;
            if (!Double.isFinite(low)) low = firstNumber(ro, "low", "min", "from", "lower", "referenceLow", "referenceMin");
            if (!Double.isFinite(high)) high = firstNumber(ro, "high", "max", "to", "upper", "referenceHigh", "referenceMax");
        }

        if (!Double.isFinite(low) || !Double.isFinite(high)) {
            String range = firstText(row,
                    "referenceRange", "referenceInterval", "referenceText", "rangeText", "referenceValues",
                    "intervalloRiferimento", "valoriRiferimento", "riferimento", "range");
            double[] parsed = parseRange(range);
            if (!Double.isFinite(low)) low = parsed[0];
            if (!Double.isFinite(high)) high = parsed[1];
        }

        if (Double.isFinite(low) && Double.isFinite(high)) {
            if (high < low) { double t = low; low = high; high = t; }
            referenceLow = low;
            referenceHigh = high;
            referenceUnit = firstText(row, "normalizedUnit", "canonicalUnit", "unit", "uom", "unita");
            referenceDate = firstText(row, "date", "clinicalDate", "issueDate", "createdAt");
        }
    }

    private static double firstNumber(JSONObject o, String... keys) {
        if (o == null) return Double.NaN;
        for (String key : keys) {
            if (!o.has(key)) continue;
            double v = parseRequestedRaw(o.opt(key));
            if (Double.isFinite(v)) return v;
        }
        return Double.NaN;
    }

    private static double[] parseRange(String raw) {
        if (raw == null) return new double[]{Double.NaN, Double.NaN};
        Matcher m = RANGE.matcher(raw.trim());
        if (!m.find()) return new double[]{Double.NaN, Double.NaN};
        try {
            return new double[]{Double.parseDouble(m.group(1).replace(',', '.')), Double.parseDouble(m.group(2).replace(',', '.'))};
        } catch (Exception ignored) {
            return new double[]{Double.NaN, Double.NaN};
        }
    }

    private static String firstText(JSONObject o, String... keys) {
        if (o == null) return "";
        for (String key : keys) {
            Object v = o.opt(key);
            if (v == null || v == JSONObject.NULL) continue;
            String s = String.valueOf(v).trim();
            if (!s.isEmpty() && !"null".equalsIgnoreCase(s)) return s;
        }
        return "";
    }

    void setEmptyText(String value) {
        if (value != null && !value.trim().isEmpty()) emptyText = value;
    }

    boolean hasData() { return !values.isEmpty(); }
    int dataCount() { return values.size(); }
    double dataMin() { return dataMin; }
    double dataMax() { return dataMax; }
    double referenceLow() { return referenceLow; }
    double referenceHigh() { return referenceHigh; }
    List<Double> dataValues() { return new ArrayList<>(values); }

    @Override protected void onDraw(Canvas canvas) {
        super.onDraw(canvas);
        boolean hasReference = Double.isFinite(referenceLow) && Double.isFinite(referenceHigh);
        float left = dp(64), right = getWidth() - dp(16), top = dp(20);
        float bottom = getHeight() - dp(hasReference ? 86 : 58);
        if (right <= left || bottom <= top) return;
        if (values.isEmpty()) {
            canvas.drawText(emptyText, left, top + dp(28), label);
            return;
        }

        double[] bounds = scaledBoundsWithReference(dataMin, dataMax, referenceLow, referenceHigh);
        double min = bounds[0], max = bounds[1];
        for (int i = 0; i <= 4; i++) {
            float y = top + (bottom - top) * i / 4f;
            canvas.drawLine(left, y, right, y, grid);
            double tick = max - (max - min) * i / 4.0;
            canvas.drawText(shortNumber(tick), dp(5), y + dp(4), label);
        }

        if (hasReference) {
            drawReferenceLine(canvas, referenceLow, min, max, left, right, top, bottom);
            if (Math.abs(referenceHigh - referenceLow) > 0.000001) {
                drawReferenceLine(canvas, referenceHigh, min, max, left, right, top, bottom);
            }
        }

        long[] times = dateTimes(dates);
        long tMin = Long.MAX_VALUE, tMax = Long.MIN_VALUE;
        for (long t : times) if (t > 0) { tMin = Math.min(tMin, t); tMax = Math.max(tMax, t); }
        boolean dated = tMin != Long.MAX_VALUE && tMax > tMin;

        Path p = new Path();
        for (int i = 0; i < values.size(); i++) {
            float x;
            if (values.size() == 1) x = (left + right) / 2f;
            else if (dated && i < times.length && times[i] > 0) x = left + (right - left) * (times[i] - tMin) / (float) (tMax - tMin);
            else x = left + (right - left) * i / (values.size() - 1f);
            float y = bottom - (float) ((values.get(i) - min) / (max - min)) * (bottom - top);
            if (i == 0) p.moveTo(x, y); else p.lineTo(x, y);
            canvas.drawCircle(x, y, dp(4.0f), point);
        }
        if (values.size() > 1) canvas.drawPath(p, line);

        if (dated) drawYearAxis(canvas, tMin, tMax, left, right, bottom);
        String unit = referenceUnit;
        if (unit == null || unit.isEmpty()) unit = firstSeriesUnit();
        if (unit != null && !unit.isEmpty()) {
            canvas.save();
            canvas.rotate(-90f, dp(18), (top + bottom) / 2f);
            canvas.drawText(unit, dp(18), (top + bottom) / 2f, label);
            canvas.restore();
        }
        String axisTitle = "Data clinica";
        float aw = label.measureText(axisTitle);
        canvas.drawText(axisTitle, Math.max(left, (getWidth() - aw) / 2f), bottom + dp(36), label);

        String footer = values.size() + " rilevazioni · min " + shortNumber(dataMin) + " · max " + shortNumber(dataMax);
        canvas.drawText(footer, left, bottom + dp(18), label);

        if (hasReference) {
            float legendY = getHeight() - dp(22);
            canvas.drawLine(left, legendY - dp(4), left + dp(28), legendY - dp(4), reference);
            String interval = "Intervallo " + shortNumber(referenceLow) + " - " + shortNumber(referenceHigh) + (unit == null || unit.isEmpty() ? "" : " " + unit);
            canvas.drawText(interval, left + dp(36), legendY, label);
            if (referenceDate != null && !referenceDate.isEmpty()) {
                String source = "Riferimento dal referto del " + displayDate(referenceDate);
                canvas.drawText(source, left + dp(36), getHeight() - dp(6), label);
            }
        }
    }

    private String firstSeriesUnit() {
        return referenceUnit == null ? "" : referenceUnit;
    }

    private void drawReferenceLine(Canvas canvas, double value, double min, double max, float left, float right, float top, float bottom) {
        if (!Double.isFinite(value) || max <= min) return;
        float y = bottom - (float) ((value - min) / (max - min)) * (bottom - top);
        if (y >= top - dp(1) && y <= bottom + dp(1)) canvas.drawLine(left, y, right, y, reference);
    }

    private void drawYearAxis(Canvas canvas, long tMin, long tMax, float left, float right, float bottom) {
        java.util.Calendar c1 = java.util.Calendar.getInstance(Locale.ITALY);
        java.util.Calendar c2 = java.util.Calendar.getInstance(Locale.ITALY);
        c1.setTimeInMillis(tMin); c2.setTimeInMillis(tMax);
        int y1 = c1.get(java.util.Calendar.YEAR), y2 = c2.get(java.util.Calendar.YEAR);
        int span = Math.max(1, y2 - y1);
        int step = span <= 8 ? 1 : span <= 30 ? 2 : span <= 60 ? 5 : 10;
        int first = (y1 / step) * step;
        if (first < y1) first += step;
        for (int year = first; year <= y2; year += step) {
            java.util.Calendar cy = java.util.Calendar.getInstance(Locale.ITALY);
            cy.clear(); cy.set(java.util.Calendar.YEAR, year); cy.set(java.util.Calendar.MONTH, 0); cy.set(java.util.Calendar.DAY_OF_MONTH, 1);
            long t = cy.getTimeInMillis();
            float x = left + (right - left) * (t - tMin) / (float) (tMax - tMin);
            if (x < left || x > right) continue;
            String text = String.valueOf(year);
            float w = label.measureText(text);
            canvas.drawText(text, Math.max(left, Math.min(right - w, x - w / 2f)), bottom + dp(18), label);
        }
    }

    private static long[] dateTimes(List<String> dates) {
        long[] out = new long[dates == null ? 0 : dates.size()];
        SimpleDateFormat iso = new SimpleDateFormat("yyyy-MM-dd", Locale.ITALY);
        SimpleDateFormat ita = new SimpleDateFormat("dd/MM/yyyy", Locale.ITALY);
        iso.setLenient(false); ita.setLenient(false);
        for (int i = 0; i < out.length; i++) {
            String raw = dates.get(i) == null ? "" : dates.get(i).trim();
            String value = raw.length() >= 10 ? raw.substring(0, 10) : raw;
            try { out[i] = iso.parse(value).getTime(); continue; } catch (Exception ignored) {}
            try { out[i] = ita.parse(value).getTime(); } catch (Exception ignored) { out[i] = 0L; }
        }
        return out;
    }

    private static String displayDate(String raw) {
        if (raw == null) return "";
        String s = raw.trim();
        if (s.length() >= 10 && s.charAt(4) == '-' && s.charAt(7) == '-') return s.substring(8,10) + "/" + s.substring(5,7) + "/" + s.substring(0,4);
        return s.length() >= 10 ? s.substring(0,10) : s;
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


# 3) HONEST, VISIBLY ACTIVE SYNC UI.
# The underlying snapshot/pull/upload methods are monolithic and expose no byte callback.
# R41 therefore removes the fake numeric percentage, keeps a horizontal animated bar,
# and updates the real operation phase before each blocking operation.
c = CLOUD.read_text(encoding='utf-8')
sync41 = r'''    public static void syncInteractiveR41(Activity activity, SharedPreferences prefs) {
        LinearLayout box = new LinearLayout(activity);
        box.setOrientation(LinearLayout.VERTICAL);
        box.setPadding(dp(activity, 22), dp(activity, 14), dp(activity, 22), dp(activity, 10));

        TextView phase = new TextView(activity);
        phase.setText("Controllo configurazione e archivio...");
        phase.setTextSize(15);
        phase.setTextColor(Color.rgb(28, 47, 43));
        box.addView(phase, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));

        android.widget.ProgressBar bar = new android.widget.ProgressBar(activity, null, android.R.attr.progressBarStyleHorizontal);
        bar.setIndeterminate(true);
        LinearLayout.LayoutParams bp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(activity, 18));
        bp.setMargins(0, dp(activity, 14), 0, dp(activity, 4));
        box.addView(bar, bp);

        TextView stage = new TextView(activity);
        stage.setText("Fase 1 di 5");
        stage.setTextSize(13);
        stage.setTextColor(Color.DKGRAY);
        box.addView(stage);

        AlertDialog dialog = new AlertDialog.Builder(activity)
                .setTitle("Sincronizzazione Dossier")
                .setView(box)
                .setCancelable(false)
                .create();
        dialog.show();

        java.util.function.BiConsumer<String,String> update = (step, message) -> activity.runOnUiThread(() -> {
            stage.setText(step);
            phase.setText(message);
        });

        EXECUTOR.execute(() -> {
            try {
                update.accept("Fase 1 di 5", "Controllo configurazione e archivio...");
                JSONObject cfg = loadConfig(prefs);
                if (cfg.optString("archiveId", "").isEmpty()) throw new Exception("Dossier cloud non configurato");

                update.accept("Fase 2 di 5", "Ricerca della copia Windows più recente...");
                boolean snapshotSafe = readArray(prefs, QUEUE_KEY).length() == 0;
                int snapshotUpdated = snapshotSafe ? r36RefreshLatestCommittedSnapshot(activity, prefs, cfg) : 0;

                update.accept("Fase 3 di 5", "Ricezione delle modifiche dal Dossier...");
                int received = pullRemoteChanges(activity, prefs, cfg, false);

                update.accept("Fase 4 di 5", "Invio delle modifiche locali...");
                int sent = uploadPendingChanges(activity, prefs, cfg);

                update.accept("Fase 5 di 5", "Verifica finale della sincronizzazione...");
                checkCompletionConsumed(activity, prefs, cfg);
                cfg.put("lastSyncAt", Instant.now().toString());
                saveConfig(prefs, cfg);
                final String result = sent + " inviate · " + received + " ricevute" + (snapshotUpdated > 0 ? " · archivio Windows aggiornato" : "");
                activity.runOnUiThread(() -> {
                    phase.setText("Sincronizzazione completata");
                    stage.setText("Completata");
                    dialog.dismiss();
                    Toast.makeText(activity, "Sincronizzazione completata · " + result, Toast.LENGTH_LONG).show();
                });
            } catch (Exception e) {
                activity.runOnUiThread(() -> {
                    dialog.dismiss();
                    new AlertDialog.Builder(activity)
                            .setTitle("Sincronizzazione non completata")
                            .setMessage(e.getMessage())
                            .setPositiveButton("Chiudi", null)
                            .show();
                });
            }
        });
    }'''
marker = '    public static void syncInteractiveR40(Activity activity, SharedPreferences prefs) {'
if marker not in c:
    raise SystemExit('R41 failed: R40 sync method missing')
c = c.replace(marker, sync41 + '\n\n' + marker, 1)

r39 = r'''    public static void syncInteractiveR39(Activity activity, SharedPreferences prefs) {
        syncInteractiveR41(activity, prefs);
    }'''
c = replace_block(c, '    public static void syncInteractiveR39(Activity activity, SharedPreferences prefs) {', r39, 'R39 entrypoint')
private_sync = r'''    private static void syncInteractive(Activity activity, SharedPreferences prefs) {
        syncInteractiveR41(activity, prefs);
    }'''
c = replace_block(c, '    private static void syncInteractive(Activity activity, SharedPreferences prefs) {', private_sync, 'cloud panel entrypoint')
CLOUD.write_text(c, encoding='utf-8')


g = GRADLE.read_text(encoding='utf-8')
if 'versionCode 40' not in g:
    raise SystemExit('R41 failed: versionCode 40 missing after R40 patches')
g = g.replace('versionCode 40', 'versionCode 41', 1)
g = g.replace("versionName '1.0.0-android-r40-global-parity-final-test'", "versionName '1.0.0-android-r41-realdevice-final-fixes-test'", 1)
GRADLE.write_text(g, encoding='utf-8')

print('R41 real-device final fixes applied')
