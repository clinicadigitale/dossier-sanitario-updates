package it.dossiersanitario.clinicadigitale.beta;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.DashPathEffect;
import android.graphics.Paint;
import android.graphics.Path;
import android.view.View;

import org.json.JSONArray;
import org.json.JSONObject;

import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.Locale;

/** Native Android rendition of the Windows Percorso peso chart. */
final class R33WeightJourneyChartView extends View {
    private final R33WeightJourneyModel.Model model;
    private final Paint grid = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint axis = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint actual = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint actualPoint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint goal = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint projection = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint marker = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint legendText = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final DateTimeFormatter shortDate = DateTimeFormatter.ofPattern("dd/MM/yy", Locale.ITALY);

    R33WeightJourneyChartView(Context context, JSONArray rows, JSONObject journey) {
        super(context);
        setMinimumHeight(dp(300));
        model = R33WeightJourneyModel.build(rows, journey);

        grid.setColor(Color.rgb(224, 232, 229));
        grid.setStrokeWidth(dp(1));
        axis.setColor(Color.rgb(91, 105, 101));
        axis.setTextSize(dp(10.5f));
        legendText.setColor(Color.rgb(91, 105, 101));
        legendText.setTextSize(dp(10.5f));

        actual.setColor(Color.rgb(37, 99, 168));
        actual.setStyle(Paint.Style.STROKE);
        actual.setStrokeWidth(dp(2.7f));
        actualPoint.setColor(Color.rgb(37, 99, 168));
        actualPoint.setStyle(Paint.Style.FILL);

        goal.setColor(Color.rgb(47, 125, 74));
        goal.setStyle(Paint.Style.STROKE);
        goal.setStrokeWidth(dp(2.1f));
        goal.setPathEffect(new DashPathEffect(new float[]{dp(7), dp(6)}, 0));

        projection.setColor(Color.rgb(180, 35, 24));
        projection.setStyle(Paint.Style.STROKE);
        projection.setStrokeWidth(dp(2.1f));
        projection.setPathEffect(new DashPathEffect(new float[]{dp(7), dp(6)}, 0));

        marker.setStyle(Paint.Style.FILL);
        setContentDescription("Grafico del percorso peso: pesate, percorso previsto e proiezione reale");
    }

    boolean hasData() { return model != null; }
    R33WeightJourneyModel.Model model() { return model; }

    @Override protected void onDraw(Canvas canvas) {
        super.onDraw(canvas);
        if (model == null) {
            canvas.drawText("Percorso peso non disponibile", dp(16), dp(30), axis);
            return;
        }

        float left = dp(54), right = getWidth() - dp(18), top = dp(24), bottom = getHeight() - dp(88);
        if (right <= left || bottom <= top) return;

        double xMin = model.startDay;
        double xMax = Math.max(model.targetDay, model.latestDay);
        if (model.predictedDay != null && Double.isFinite(model.predictedDay)) xMax = Math.max(xMax, model.predictedDay);
        if (xMax <= xMin) xMax = xMin + 1.0;

        double yMin = Math.min(model.startWeight, model.targetWeight);
        double yMax = Math.max(model.startWeight, model.targetWeight);
        for (R33WeightJourneyModel.Point p : model.actual) {
            yMin = Math.min(yMin, p.value);
            yMax = Math.max(yMax, p.value);
        }
        double span = Math.max(2.0, yMax - yMin);
        double pad = Math.max(1.0, span * 0.08);
        yMin = Math.max(0.0, Math.floor((yMin - pad) * 2.0) / 2.0);
        yMax = Math.ceil((yMax + pad) * 2.0) / 2.0;
        if (yMax <= yMin) yMax = yMin + 2.0;

        canvas.drawText("Peso (kg)", left, dp(14), axis);

        for (int i = 0; i < 6; i++) {
            double v = yMax - (i / 5.0) * (yMax - yMin);
            float y = y(v, yMin, yMax, top, bottom);
            canvas.drawLine(left, y, right, y, grid);
            canvas.drawText(R33WeightJourneyModel.fmt(v), dp(4), y + dp(4), axis);
        }

        for (int i = 0; i < 5; i++) {
            double day = xMin + (i / 4.0) * (xMax - xMin);
            float x = x(day, xMin, xMax, left, right);
            canvas.drawLine(x, top, x, bottom, grid);
            String label = dayLabel(day);
            float w = axis.measureText(label);
            canvas.drawText(label, Math.max(left, Math.min(right - w, x - w / 2f)), bottom + dp(17), axis);
        }

        // Theoretical Windows trajectory: start date/weight -> target date/weight.
        canvas.drawLine(
                x(model.startDay, xMin, xMax, left, right), y(model.startWeight, yMin, yMax, top, bottom),
                x(model.targetDay, xMin, xMax, left, right), y(model.targetWeight, yMin, yMax, top, bottom), goal);

        // Real weigh-ins from the journey start date only.
        if (!model.actual.isEmpty()) {
            Path path = new Path();
            for (int i = 0; i < model.actual.size(); i++) {
                R33WeightJourneyModel.Point p = model.actual.get(i);
                float px = x(p.day, xMin, xMax, left, right);
                float py = y(p.value, yMin, yMax, top, bottom);
                if (i == 0) path.moveTo(px, py); else path.lineTo(px, py);
                canvas.drawCircle(px, py, dp(3.8f), actualPoint);
            }
            if (model.actual.size() > 1) canvas.drawPath(path, actual);
        }

        // Robust Windows projection from the latest actual reading to the target weight.
        if (model.predictedDay != null && Double.isFinite(model.predictedDay) && Double.isFinite(model.slope)) {
            canvas.drawLine(
                    x(model.latestDay, xMin, xMax, left, right), y(model.latestWeight, yMin, yMax, top, bottom),
                    x(model.predictedDay, xMin, xMax, left, right), y(model.targetWeight, yMin, yMax, top, bottom), projection);
            marker.setColor(Color.rgb(180, 35, 24));
            canvas.drawCircle(x(model.predictedDay, xMin, xMax, left, right), y(model.targetWeight, yMin, yMax, top, bottom), dp(4.3f), marker);
        }

        marker.setColor(Color.rgb(47, 125, 74));
        canvas.drawCircle(x(model.targetDay, xMin, xMax, left, right), y(model.targetWeight, yMin, yMax, top, bottom), dp(4.3f), marker);

        // Explicit endpoint labels, as on Windows.
        String targetText = "Obiettivo " + dayLabel(model.targetDay);
        drawEndpoint(canvas, targetText, x(model.targetDay, xMin, xMax, left, right), bottom + dp(36), Color.rgb(47, 125, 74), left, right);
        if (model.predictedDay != null && Double.isFinite(model.predictedDay)) {
            String estimated = "Stima " + dayLabel(model.predictedDay);
            drawEndpoint(canvas, estimated, x(model.predictedDay, xMin, xMax, left, right), bottom + dp(51), Color.rgb(180, 35, 24), left, right);
        }

        // Legend intentionally below the graph, matching Windows.
        float legendY = getHeight() - dp(14);
        float cursor = left;
        cursor = legend(canvas, cursor, legendY, Color.rgb(37, 99, 168), false, "Pesate");
        cursor = legend(canvas, cursor + dp(12), legendY, Color.rgb(47, 125, 74), true, "Percorso previsto");
        legend(canvas, cursor + dp(12), legendY, Color.rgb(180, 35, 24), true, "Proiezione reale");
    }

    private void drawEndpoint(Canvas canvas, String text, float x, float y, int color, float left, float right) {
        Paint p = new Paint(axis);
        p.setColor(color);
        p.setFakeBoldText(true);
        float w = p.measureText(text);
        float tx = Math.max(left, Math.min(right - w, x - w / 2f));
        canvas.drawText(text, tx, y, p);
    }

    private float legend(Canvas canvas, float x, float y, int color, boolean dashed, String text) {
        Paint p = new Paint(Paint.ANTI_ALIAS_FLAG);
        p.setColor(color);
        p.setStrokeWidth(dp(2));
        if (dashed) p.setPathEffect(new DashPathEffect(new float[]{dp(6), dp(5)}, 0));
        canvas.drawLine(x, y - dp(4), x + dp(20), y - dp(4), p);
        canvas.drawText(text, x + dp(25), y, legendText);
        return x + dp(25) + legendText.measureText(text);
    }

    private String dayLabel(double epochDay) {
        try { return LocalDate.ofEpochDay(Math.round(epochDay)).format(shortDate); }
        catch (Exception ignored) { return ""; }
    }

    private float x(double day, double min, double max, float left, float right) {
        return left + (float) ((day - min) / (max - min)) * (right - left);
    }

    private float y(double value, double min, double max, float top, float bottom) {
        return bottom - (float) ((value - min) / (max - min)) * (bottom - top);
    }

    private int dp(float value) { return Math.round(value * getResources().getDisplayMetrics().density); }
}
