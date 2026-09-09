from pathlib import Path

CHART = Path('android-r3/app/src/main/java/it/dossiersanitario/clinicadigitale/beta/R26ChartView.java')
s = CHART.read_text(encoding='utf-8')

needle = '    private String referenceUnit = "";\n    private String referenceDate = "";'
if needle not in s:
    raise SystemExit('R41 unit fix: fields missing')
s = s.replace(needle, '    private String referenceUnit = "";\n    private String seriesUnit = "";\n    private String referenceDate = "";', 1)

needle = '''                JSONObject o = records.optJSONObject(i);\n                double v = requestedValue(o, preferredKeys);'''
replacement = '''                JSONObject o = records.optJSONObject(i);\n                if (seriesUnit.isEmpty() && o != null) {\n                    seriesUnit = firstText(o, "normalizedUnit", "canonicalUnit", "unit", "uom", "unita");\n                }\n                double v = requestedValue(o, preferredKeys);'''
if needle not in s:
    raise SystemExit('R41 unit fix: constructor ingest missing')
s = s.replace(needle, replacement, 1)

needle = '''        String unit = referenceUnit;\n        if (unit == null || unit.isEmpty()) unit = firstSeriesUnit();'''
replacement = '''        String unit = referenceUnit;\n        if (unit == null || unit.isEmpty()) unit = seriesUnit;'''
if needle not in s:
    raise SystemExit('R41 unit fix: unit selection missing')
s = s.replace(needle, replacement, 1)

# Remove obsolete helper if present.
old = '''    private String firstSeriesUnit() {\n        return referenceUnit == null ? "" : referenceUnit;\n    }\n\n'''
s = s.replace(old, '', 1)
CHART.write_text(s, encoding='utf-8')
print('R41 all-graph unit label fix applied')
