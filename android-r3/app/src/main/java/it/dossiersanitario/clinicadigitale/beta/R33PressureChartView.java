package it.dossiersanitario.clinicadigitale.beta;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Path;
import android.view.View;

import org.json.JSONArray;
import org.json.JSONObject;

import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;

/** Windows-compatible pressure chart: systolic and diastolic in one graph. */
final class R33PressureChartView extends View {
    private static final class Point {
        final double day;
        final double systolic;
        final double diastolic;
        Point(double day, double systolic, double diastolic) {
            this.day = day; this.systolic = systolic; this.diastolic = diastolic;
        }
    }

    private final List<Point> points = new ArrayList<>();
    private final Paint grid = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint axis = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint sys = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint dia = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint pointSys = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint pointDia = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint legend = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final DateTimeFormatter shortDate = DateTimeFormatter.ofPattern("dd/MM/yy", Locale.ITALY);

    R33PressureChartView(Context context, JSONArray rows, int primary) {
        super(context);
        setMinimumHeight(dp(255));
        grid.setColor(Color.rgb(224, 232, 229)); grid.setStrokeWidth(dp(1));
        axis.setColor(Color.rgb(91, 105, 101)); axis.setTextSize(dp(10.5f));
        legend.setColor(Color.rgb(91, 105, 101)); legend.setTextSize(dp(10.5f));
        sys.setColor(primary); sys.setStyle(Paint.Style.STROKE); sys.setStrokeWidth(dp(2.7f));
        dia.setColor(Color.rgb(122, 122, 122)); dia.setStyle(Paint.Style.STROKE); dia.setStrokeWidth(dp(2.7f));
        pointSys.setColor(primary); pointDia.setColor(Color.rgb(122, 122, 122));

        if (rows != null) {
            for (int i = 0; i < rows.length(); i++) {
                JSONObject row = rows.optJSONObject(i); if (row == null) continue;
                Double day = parseDateTime(row.optString("date", ""), row.optString("time", ""));
                double s = number(row.opt("systolic"));
                double d = number(row.opt("diastolic"));
                if (day == null || (!Double.isFinite(s) && !Double.isFinite(d))) continue;
                points.add(new Point(day, s, d));
            }
        }
        points.sort(Comparator.comparingDouble(p -> p.day));
        setContentDescription("Grafico pressione arteriosa con sistolica e diastolica");
    }

    boolean hasData() { return !points.isEmpty(); }

    @Override protected void onDraw(Canvas canvas) {
        super.onDraw(canvas);
        float left = dp(50), right = getWidth() - dp(16), top = dp(22), bottom = getHeight() - dp(62);
        if (right <= left || bottom <= top) return;
        if (points.isEmpty()) {
            canvas.drawText("Nessun dato pressorio disponibile", left, top + dp(24), axis);
            return;
        }

        double xMin = points.get(0).day, xMax = points.get(points.size() - 1).day;
        if (xMax <= xMin) xMax = xMin + 1.0;
        double yMin = Double.POSITIVE_INFINITY, yMax = Double.NEGATIVE_INFINITY;
        for (Point p : points) {
            if (Double.isFinite(p.systolic)) { yMin = Math.min(yMin, p.systolic); yMax = Math.max(yMax, p.systolic); }
            if (Double.isFinite(p.diastolic)) { yMin = Math.min(yMin, p.diastolic); yMax = Math.max(yMax, p.diastolic); }
        }
        if (!Double.isFinite(yMin) || !Double.isFinite(yMax)) return;
        if (Math.abs(yMax - yMin) < 1.0) { yMin -= 5; yMax += 5; }
        double pad = Math.max(5.0, (yMax - yMin) * 0.08);
        yMin = Math.max(0.0, Math.floor((yMin - pad) / 5.0) * 5.0);
        yMax = Math.ceil((yMax + pad) / 5.0) * 5.0;

        canvas.drawText("mmHg", left, dp(14), axis);
        for (int i = 0; i < 6; i++) {
            double v = yMax - (i / 5.0) * (yMax - yMin);
            float yy = y(v, yMin, yMax, top, bottom);
            canvas.drawLine(left, yy, right, yy, grid);
            canvas.drawText(String.valueOf((int) Math.round(v)), dp(4), yy + dp(4), axis);
        }
        for (int i = 0; i < 5; i++) {
            double day = xMin + (i / 4.0) * (xMax - xMin);
            float xx = x(day, xMin, xMax, left, right);
            canvas.drawLine(xx, top, xx, bottom, grid);
            String txt = date(day);
            float w = axis.measureText(txt);
            canvas.drawText(txt, Math.max(left, Math.min(right - w, xx - w / 2f)), bottom + dp(17), axis);
        }

        drawSeries(canvas, true, xMin, xMax, yMin, yMax, left, right, top, bottom);
        drawSeries(canvas, false, xMin, xMax, yMin, yMax, left, right, top, bottom);

        float ly = getHeight() - dp(14);
        canvas.drawLine(left, ly - dp(4), left + dp(22), ly - dp(4), sys);
        canvas.drawText("Sistolica", left + dp(28), ly, legend);
        float second = left + dp(28) + legend.measureText("Sistolica") + dp(18);
        canvas.drawLine(second, ly - dp(4), second + dp(22), ly - dp(4), dia);
        canvas.drawText("Diastolica", second + dp(28), ly, legend);
    }

    private void drawSeries(Canvas canvas, boolean systolic, double xMin, double xMax, double yMin, double yMax,
                            float left, float right, float top, float bottom) {
        Paint line = systolic ? sys : dia;
        Paint dot = systolic ? pointSys : pointDia;
        Path path = new Path(); boolean started = false;
        for (Point p : points) {
            double value = systolic ? p.systolic : p.diastolic;
            if (!Double.isFinite(value)) continue;
            float xx = x(p.day, xMin, xMax, left, right);
            float yy = y(value, yMin, yMax, top, bottom);
            if (!started) { path.moveTo(xx, yy); started = true; } else path.lineTo(xx, yy);
            canvas.drawCircle(xx, yy, dp(3.5f), dot);
        }
        if (started) canvas.drawPath(path, line);
    }

    private String date(double day) {
        try { return LocalDate.ofEpochDay(Math.round(day)).format(shortDate); }
        catch (Exception ignored) { return ""; }
    }

    private float x(double day, double min, double max, float left, float right) {
        return left + (float) ((day - min) / (max - min)) * (right - left);
    }
    private float y(double v, double min, double max, float top, float bottom) {
        return bottom - (float) ((v - min) / (max - min)) * (bottom - top);
    }
    private int dp(float v) { return Math.round(v * getResources().getDisplayMetrics().density); }

    private static double number(Object raw) {
        if (raw == null || raw == JSONObject.NULL) return Double.NaN;
        try { return Double.parseDouble(String.valueOf(raw).replace(',', '.').trim()); }
        catch (Exception ignored) { return Double.NaN; }
    }
    private static Double parseDateTime(String iso, String time) {
        try {
            double day = LocalDate.parse(iso).toEpochDay();
            int minutes = 12 * 60;
            String t = time == null ? "" : time.trim();
            if (t.matches("\\d{1,2}:\\d{2}.*")) {
                String[] parts = t.substring(0, Math.min(5, t.length())).split(":");
                minutes = Integer.parseInt(parts[0]) * 60 + Integer.parseInt(parts[1]);
            }
            return day + minutes / 1440.0;
        } catch (Exception ignored) { return null; }
    }
}
