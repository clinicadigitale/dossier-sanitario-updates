package it.dossiersanitario.clinicadigitale.beta;

import org.json.JSONArray;
import org.json.JSONObject;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;

/** Windows V8 compatible weight-journey calculations used by the Android monitor. */
final class R33WeightJourneyModel {
    static final class Point {
        final JSONObject row;
        final double day;
        final double value;
        Point(JSONObject row, double day, double value) { this.row = row; this.day = day; this.value = value; }
    }

    static final class Model {
        final JSONObject journey;
        final List<Point> actual;
        final double startDay;
        final double targetDay;
        final double startWeight;
        final double targetWeight;
        final double latestDay;
        final double latestWeight;
        final double slope;
        final Double predictedDay;
        final int pathDelayDays;
        final double pathDeviationKg;
        final double expectedAtLatest;
        final double plannedSlope;
        final Integer forecastDeltaDays;
        final String trendMethod;

        Model(JSONObject journey, List<Point> actual, double startDay, double targetDay,
              double startWeight, double targetWeight, double latestDay, double latestWeight,
              double slope, Double predictedDay, int pathDelayDays, double pathDeviationKg,
              double expectedAtLatest, double plannedSlope, Integer forecastDeltaDays,
              String trendMethod) {
            this.journey = journey;
            this.actual = actual;
            this.startDay = startDay;
            this.targetDay = targetDay;
            this.startWeight = startWeight;
            this.targetWeight = targetWeight;
            this.latestDay = latestDay;
            this.latestWeight = latestWeight;
            this.slope = slope;
            this.predictedDay = predictedDay;
            this.pathDelayDays = pathDelayDays;
            this.pathDeviationKg = pathDeviationKg;
            this.expectedAtLatest = expectedAtLatest;
            this.plannedSlope = plannedSlope;
            this.forecastDeltaDays = forecastDeltaDays;
            this.trendMethod = trendMethod;
        }

        String predictedIso() {
            if (predictedDay == null || !Double.isFinite(predictedDay)) return "";
            return LocalDate.ofEpochDay(Math.round(predictedDay)).toString();
        }

        double progressPercent() {
            double total = targetWeight - startWeight;
            if (Math.abs(total) < 1e-9) return 100.0;
            double value = ((latestWeight - startWeight) / total) * 100.0;
            return Math.max(0.0, Math.min(100.0, value));
        }

        long daysTotal() { return Math.max(1L, Math.round(targetDay - startDay)); }
        long daysRemaining() {
            double today = LocalDate.now().toEpochDay();
            return Math.max(0L, Math.round(targetDay - today));
        }
        double weeklyRequired() { return Math.abs(targetWeight - startWeight) / (daysTotal() / 7.0); }
    }

    private R33WeightJourneyModel() {}

    static Model build(JSONArray rows, JSONObject journey) {
        if (journey == null) return null;
        Double startDay = parseDate(journey.optString("startDate", ""));
        Double targetDay = parseDate(journey.optString("targetDate", ""));
        double startWeight = number(journey, "startWeight");
        double targetWeight = number(journey, "targetWeight");
        if (startDay == null || targetDay == null || !Double.isFinite(startWeight) || !Double.isFinite(targetWeight)) return null;

        List<Point> actual = new ArrayList<>();
        if (rows != null) {
            for (int i = 0; i < rows.length(); i++) {
                JSONObject row = rows.optJSONObject(i);
                if (row == null) continue;
                Double day = parseDateTime(row.optString("date", ""), row.optString("time", ""));
                double value = number(row, "value");
                if (day == null || !Double.isFinite(value) || day < startDay) continue;
                actual.add(new Point(row, day, value));
            }
        }
        actual.sort(Comparator.comparingDouble(p -> p.day));

        Point latest = actual.isEmpty() ? new Point(null, startDay, startWeight) : actual.get(actual.size() - 1);
        double direction = Math.signum(targetWeight - latest.value);
        double slope = Double.NaN;
        Double predictedDay = null;
        String trendMethod = "";

        if (Math.abs(targetWeight - latest.value) < 0.05) {
            predictedDay = latest.day;
            trendMethod = "target-reached";
        } else {
            List<Point> recent = actual.subList(Math.max(0, actual.size() - 8), actual.size());
            List<Double> slopes = new ArrayList<>();
            if (recent.size() >= 4) {
                for (int i = 0; i < recent.size(); i++) {
                    for (int j = i + 1; j < recent.size(); j++) {
                        double days = recent.get(j).day - recent.get(i).day;
                        if (days >= 1.0) slopes.add((recent.get(j).value - recent.get(i).value) / days);
                    }
                }
                Collections.sort(slopes);
                if (!slopes.isEmpty()) {
                    int mid = slopes.size() / 2;
                    double robust = slopes.size() % 2 == 1 ? slopes.get(mid) : (slopes.get(mid - 1) + slopes.get(mid)) / 2.0;
                    if (Double.isFinite(robust) && Math.abs(robust) >= 0.003 && towardsTarget(direction, robust)) {
                        slope = robust;
                        trendMethod = "recent-robust";
                    }
                }
            }
            if (!Double.isFinite(slope)) {
                double elapsed = Math.max(0.0, latest.day - startDay);
                double netSlope = elapsed >= 2.0 ? (latest.value - startWeight) / elapsed : Double.NaN;
                if (Double.isFinite(netSlope) && Math.abs(netSlope) >= 0.003 && towardsTarget(direction, netSlope)) {
                    slope = netSlope;
                    trendMethod = "net-progress-fallback";
                }
            }
            if (Double.isFinite(slope)) {
                double days = (targetWeight - latest.value) / slope;
                double plannedDays = Math.max(1.0, targetDay - startDay);
                double maxForecastDays = Math.max(365.0, plannedDays * 3.0);
                if (Double.isFinite(days) && days >= 0.0 && days <= maxForecastDays) predictedDay = latest.day + days;
            }
        }

        double plannedDays = Math.max(1.0, targetDay - startDay);
        double plannedSlope = (targetWeight - startWeight) / plannedDays;
        double elapsedLatest = Math.max(0.0, Math.min(plannedDays, latest.day - startDay));
        double expectedAtLatest = startWeight + plannedSlope * elapsedLatest;
        double pathDeviationKg = latest.value - expectedAtLatest;
        int pathDelayDays = Double.isFinite(plannedSlope) && Math.abs(plannedSlope) > 1e-9
                ? (int) Math.round(-pathDeviationKg / plannedSlope) : 0;
        Integer forecastDeltaDays = predictedDay == null ? null : (int) Math.round(predictedDay - targetDay);

        return new Model(journey, actual, startDay, targetDay, startWeight, targetWeight,
                latest.day, latest.value, slope, predictedDay, pathDelayDays, pathDeviationKg,
                expectedAtLatest, plannedSlope, forecastDeltaDays, trendMethod);
    }

    static JSONObject activeJourney(JSONArray journeys) {
        if (journeys == null || journeys.length() == 0) return null;
        JSONObject first = null;
        for (int i = 0; i < journeys.length(); i++) {
            JSONObject row = journeys.optJSONObject(i);
            if (row == null) continue;
            if (first == null) first = row;
            if ("active".equalsIgnoreCase(row.optString("status", ""))) return row;
        }
        return first;
    }

    static double bmi(double weightKg, double heightCm) {
        double h = heightCm / 100.0;
        if (!Double.isFinite(weightKg) || !Double.isFinite(h) || weightKg <= 0 || h <= 0) return Double.NaN;
        return weightKg / (h * h);
    }

    static String weightBmi(double weightKg, double heightCm) {
        if (!Double.isFinite(weightKg)) return "—";
        double bmi = bmi(weightKg, heightCm);
        String weight = fmt(weightKg) + " kg";
        return Double.isFinite(bmi) ? weight + " / BMI " + String.format(Locale.ITALY, "%.1f", bmi) : weight;
    }

    static String fmt(double value) {
        if (!Double.isFinite(value)) return "—";
        if (Math.abs(value - Math.rint(value)) < 0.05) return String.valueOf((long) Math.rint(value));
        return String.format(Locale.ITALY, "%.1f", value);
    }

    private static boolean towardsTarget(double direction, double slope) {
        return (direction < 0 && slope < 0) || (direction > 0 && slope > 0);
    }

    private static double number(JSONObject row, String key) {
        if (row == null) return Double.NaN;
        Object raw = row.opt(key);
        if (raw == null || raw == JSONObject.NULL) return Double.NaN;
        try { return Double.parseDouble(String.valueOf(raw).replace(',', '.').trim()); }
        catch (Exception ignored) { return Double.NaN; }
    }

    private static Double parseDate(String iso) {
        try { return (double) LocalDate.parse(iso).toEpochDay(); }
        catch (Exception ignored) { return null; }
    }

    private static Double parseDateTime(String iso, String time) {
        Double day = parseDate(iso);
        if (day == null) return null;
        int minutes = 12 * 60;
        try {
            String t = time == null ? "" : time.trim();
            if (t.matches("\\d{1,2}:\\d{2}.*")) {
                String[] parts = t.substring(0, Math.min(5, t.length())).split(":");
                minutes = Integer.parseInt(parts[0]) * 60 + Integer.parseInt(parts[1]);
            }
        } catch (Exception ignored) {}
        return day + minutes / 1440.0;
    }
}
