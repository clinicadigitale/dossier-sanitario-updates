package it.dossiersanitario.clinicadigitale.beta;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Path;
import android.view.View;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

/** R38 chart: exact selected values, tight dynamic domain, visible point values. */
final class R38ChartView extends View {
    private final Paint grid = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint line = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint point = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint label = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint valueLabel = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final List<Double> values = new ArrayList<>();
    private final List<String> dates = new ArrayList<>();
    private final R38GraphMath.Domain domain;

    R38ChartView(Context context, JSONArray normalizedRows, int accent) {
        super(context);
        setMinimumHeight(dp(270));
        grid.setColor(Color.rgb(224, 232, 229));
        grid.setStrokeWidth(dp(1));
        line.setColor(accent);
        line.setStrokeWidth(dp(3));
        line.setStyle(Paint.Style.STROKE);
        point.setColor(accent);
        point.setStyle(Paint.Style.FILL);
        label.setColor(Color.rgb(91, 105, 101));
        label.setTextSize(dp(10.5f));
        valueLabel.setColor(accent);
        valueLabel.setTextSize(dp(10.5f));
        valueLabel.setFakeBoldText(true);

        if (normalizedRows != null) {
            for (int i = 0; i < normalizedRows.length(); i++) {
                JSONObject row = normalizedRows.optJSONObject(i);
                if (row == null) continue;
                double value = number(row.opt("value"));
                if (!Double.isFinite(value)) continue;
                values.add(value);
                dates.add(date(row));
            }
        }
        double[] raw = new double[values.size()];
        for (int i = 0; i < values.size(); i++) raw[i] = values.get(i);
        domain = R38GraphMath.domain(raw);
        setContentDescription("Grafico clinico con valori reali della serie selezionata");
    }

    boolean hasData() { return !values.isEmpty(); }
    boolean hasVariation() { return domain.varied; }

    @Override protected void onDraw(Canvas canvas) {
        super.onDraw(canvas);
        float left = dp(58), right = getWidth() - dp(18), top = dp(24), bottom = getHeight() - dp(54);
        if (right <= left || bottom <= top) return;
        if (values.isEmpty()) {
            canvas.drawText("Nessun dato numerico disponibile", left, top + dp(28), label);
            return;
        }

        for (int i = 0; i <= 5; i++) {
            float y = top + (bottom - top) * i / 5f;
            canvas.drawLine(left, y, right, y, grid);
            double v = domain.max - (domain.max - domain.min) * i / 5.0;
            canvas.drawText(shortNumber(v), dp(4), y + dp(4), label);
        }

        Path path = new Path();
        int n = values.size();
        int labelEvery = n <= 10 ? 1 : Math.max(1, (int) Math.ceil(n / 8.0));
        for (int i = 0; i < n; i++) {
            float x = n == 1 ? (left + right) / 2f : left + (right - left) * i / (n - 1f);
            float y = R38GraphMath.y(values.get(i), domain, top, bottom);
            if (i == 0) path.moveTo(x, y); else path.lineTo(x, y);
            canvas.drawCircle(x, y, dp(4.0f), point);
            if (i == 0 || i == n - 1 || i % labelEvery == 0) {
                String txt = shortNumber(values.get(i));
                float w = valueLabel.measureText(txt);
                float ty = Math.max(top + dp(12), y - dp(9));
                canvas.drawText(txt, Math.max(left, Math.min(right - w, x - w / 2f)), ty, valueLabel);
            }
        }
        if (n > 1) canvas.drawPath(path, line);

        String first = dates.isEmpty() ? "" : compactDate(dates.get(0));
        String last = dates.isEmpty() ? "" : compactDate(dates.get(dates.size() - 1));
        if (!first.isEmpty()) canvas.drawText(first, left, getHeight() - dp(18), label);
        if (!last.isEmpty()) {
            float w = label.measureText(last);
            canvas.drawText(last, Math.max(left, right - w), getHeight() - dp(18), label);
        }
        String count = n + (n == 1 ? " rilevazione" : " rilevazioni");
        float cw = label.measureText(count);
        canvas.drawText(count, Math.max(left, (left + right - cw) / 2f), getHeight() - dp(18), label);

        if (!domain.varied && n > 1) {
            String same = "Valori identici nelle rilevazioni disponibili";
            float w = label.measureText(same);
            canvas.drawText(same, Math.max(left, (left + right - w) / 2f), top + dp(15), label);
        }
    }

    private String date(JSONObject row) {
        String[] keys = {"date", "clinicalDate", "issueDate", "documentDate", "createdAt", "updatedAt"};
        for (String key : keys) {
            String value = row.optString(key, "").trim();
            if (!value.isEmpty()) return value;
        }
        return "";
    }

    private String compactDate(String raw) {
        if (raw == null) return "";
        String s = raw.trim();
        if (s.length() >= 10 && s.charAt(4) == '-' && s.charAt(7) == '-') {
            return s.substring(8,10) + "/" + s.substring(5,7) + "/" + s.substring(2,4);
        }
        return s.length() > 10 ? s.substring(0,10) : s;
    }

    private String shortNumber(double v) {
        if (Math.abs(v - Math.rint(v)) < 0.005) return String.valueOf((long) Math.rint(v));
        if (Math.abs(v) >= 100) return String.format(Locale.ITALY, "%.1f", v);
        return String.format(Locale.ITALY, "%.2f", v).replaceAll("0+$", "").replaceAll(",$", "");
    }

    private static double number(Object raw) {
        if (raw == null || raw == JSONObject.NULL) return Double.NaN;
        if (raw instanceof Number) return ((Number) raw).doubleValue();
        try { return Double.parseDouble(String.valueOf(raw).trim().replace(',', '.')); }
        catch (Exception ignored) { return Double.NaN; }
    }

    private int dp(float value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }
}
