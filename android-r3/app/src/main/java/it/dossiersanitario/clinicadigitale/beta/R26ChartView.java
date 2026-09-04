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

/** Lightweight native line chart for health-series imported from Windows. */
final class R26ChartView extends View {
    private final Paint grid = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint line = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint point = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint label = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final List<Double> values = new ArrayList<>();
    private String emptyText = "Nessun dato numerico disponibile";

    R26ChartView(Context context, JSONArray records, int accent, String... preferredKeys) {
        super(context);
        setMinimumHeight(dp(220));
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
                double v = R26SnapshotBridge.numericValue(o, preferredKeys);
                if (!Double.isNaN(v) && !Double.isInfinite(v)) values.add(v);
            }
        }
    }

    void setEmptyText(String value) {
        if (value != null && !value.trim().isEmpty()) emptyText = value;
    }

    boolean hasData() { return values.size() > 0; }

    @Override protected void onDraw(Canvas canvas) {
        super.onDraw(canvas);
        float left = dp(46), right = getWidth() - dp(16), top = dp(18), bottom = getHeight() - dp(34);
        if (right <= left || bottom <= top) return;
        for (int i = 0; i <= 4; i++) {
            float y = top + (bottom - top) * i / 4f;
            canvas.drawLine(left, y, right, y, grid);
        }
        if (values.isEmpty()) {
            canvas.drawText(emptyText, left, top + dp(28), label);
            return;
        }
        double min = values.get(0), max = values.get(0);
        for (double v : values) { if (v < min) min = v; if (v > max) max = v; }
        if (Math.abs(max - min) < 0.0001) { min -= 1; max += 1; }
        double margin = Math.max((max - min) * 0.08, 0.5);
        min -= margin; max += margin;

        canvas.drawText(shortNumber(max), dp(4), top + dp(5), label);
        canvas.drawText(shortNumber(min), dp(4), bottom, label);

        Path p = new Path();
        for (int i = 0; i < values.size(); i++) {
            float x = values.size() == 1 ? (left + right) / 2f : left + (right - left) * i / (values.size() - 1f);
            float y = bottom - (float) ((values.get(i) - min) / (max - min)) * (bottom - top);
            if (i == 0) p.moveTo(x, y); else p.lineTo(x, y);
            canvas.drawCircle(x, y, dp(3.5f), point);
        }
        canvas.drawPath(p, line);
        canvas.drawText(values.size() + " rilevazioni", left, getHeight() - dp(8), label);
    }

    private String shortNumber(double v) {
        if (Math.abs(v - Math.rint(v)) < 0.05) return String.valueOf((long) Math.rint(v));
        return String.format(java.util.Locale.ITALY, "%.1f", v);
    }

    private int dp(float value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }
}