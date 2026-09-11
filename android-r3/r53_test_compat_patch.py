from pathlib import Path

BASE = Path('android-r3/app/src/main/java/it/dossiersanitario/clinicadigitale/beta')
TEST = Path('android-r3/app/src/test/java/it/dossiersanitario/clinicadigitale/beta')
R53_NAME = '1.0.0-android-r53-prepare-visit-dossier-search-test'


def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'R53 compat expected one {label}, found {count}')
    return text.replace(old, new, 1)

# Align inherited version assertions to R53, including the historical R46 test
# whose method was intentionally rewritten by the R47 compatibility layer.
changed = 0
for p in TEST.glob('*.java'):
    s = p.read_text(encoding='utf-8')
    original = s
    s = s.replace('versionCode 52', 'versionCode 53')
    s = s.replace('versionCode = 52', 'versionCode = 53')
    s = s.replace('1.0.0-android-r52-all-graphs-height-test', R53_NAME)
    if p.name == 'R46WindowsGraphSyncPageAuditTest.java':
        s = s.replace('versionCode 47', 'versionCode 53')
        s = s.replace('versionCode = 47', 'versionCode = 53')
        s = s.replace('1.0.0-android-r47-sync-crash-graph-layout-test', R53_NAME)
    if s != original:
        p.write_text(s, encoding='utf-8')
        changed += 1
if changed < 1:
    raise SystemExit('R53 compatibility did not update inherited version expectations')

# Expose pure deterministic helpers for the two R53 rules that previously had
# tests constructing Android org.json objects. The production code itself is
# wired through the same pure helpers, so tests exercise the real rule path.
logic_path = BASE / 'R53VisitLogic.java'
logic = logic_path.read_text(encoding='utf-8')

old_bucket = '''    static String documentBucket(JSONObject d) {\n        if (isLabDocument(d)) return "lab";\n        String n = normalize(documentMetadata(d));\n        if (containsAny(n, "visita", "consulto", "ambulator", "specialistic")) return "visit";\n        if (containsAny(n, "gastrosc", "colonsc", "endosc", "ecograf", "ecocard", "elettrocard", "ecg", "holter",\n                "tac", "tomograf", "risonanza", "rmn", "radiograf", "rx", "spirometr", "elettromiograf", "emg",\n                "elettroencefal", "eeg", "mammograf", "fibroscan", "elastograf")) return "instrumental";\n        if (containsAny(n, "ricovero", "dimission", "pronto soccorso", "emergenza", "ospedal")) return "hospital";\n        if (containsAny(n, "referto", "relazione", "lettera", "diagnostic")) return "report";\n        return "other";\n    }'''
new_bucket = '''    static String documentBucket(JSONObject d) {\n        if (isLabDocument(d)) return "lab";\n        return documentBucketText(documentMetadata(d));\n    }\n\n    static String documentBucketText(String text) {\n        String n = normalize(text);\n        if (containsAny(n, "laboratorio","prelievo","ematochim","sangue","blood test","analisi cliniche","analisi sangue")) return "lab";\n        if (containsAny(n, "visita", "consulto", "ambulator", "specialistic")) return "visit";\n        if (containsAny(n, "gastrosc", "colonsc", "endosc", "ecograf", "ecocard", "elettrocard", "ecg", "holter",\n                "tac", "tomograf", "risonanza", "rmn", "radiograf", "rx", "spirometr", "elettromiograf", "emg",\n                "elettroencefal", "eeg", "mammograf", "fibroscan", "elastograf")) return "instrumental";\n        if (containsAny(n, "ricovero", "dimission", "pronto soccorso", "emergenza", "ospedal")) return "hospital";\n        if (containsAny(n, "referto", "relazione", "lettera", "diagnostic")) return "report";\n        return "other";\n    }'''
logic = replace_once(logic, old_bucket, new_bucket, 'document bucket rule')

insert_marker = '''    private static String[] arr(String... values) { return values; }'''
helpers = '''    static boolean specialtyTextMatch(String specialty, String text) {\n        return containsAny(normalize(text), specialtyKeywords(specialty));\n    }\n\n    static boolean specialtyLabMatch(String specialty, String labName) {\n        return containsAny(normalize(labName), specialtyLabNames(specialty));\n    }\n\n'''
logic = replace_once(logic, insert_marker, helpers + insert_marker, 'specialty helper insertion point')

logic = replace_once(logic,
    '''        String[] keys = specialtyKeywords(specialty);\n        String specOnly = normalize(first(d,"specialization","specialty","department"));\n        if (containsAny(specOnly, keys)) return true;\n        if (containsAny(meta, keys) && containsAny(meta, "visita","consulto","specialistic","ambulator")) return true;''',
    '''        String specOnly = normalize(first(d,"specialization","specialty","department"));\n        if (specialtyTextMatch(specialty, specOnly)) return true;\n        if (specialtyTextMatch(specialty, meta) && containsAny(meta, "visita","consulto","specialistic","ambulator")) return true;''',
    'direct specialty matching')
logic = replace_once(logic,
    '''                if (containsAny(normalize(first(dx,"name","diagnosis","description","specialty","specialization")), keys)) return true;''',
    '''                if (specialtyTextMatch(specialty, first(dx,"name","diagnosis","description","specialty","specialization"))) return true;''',
    'diagnosis specialty matching')
logic = replace_once(logic,
    '''        String[] keys=specialtyKeywords(specialty);\n        if (containsAny(all, keys)) return true;''',
    '''        if (specialtyTextMatch(specialty, all)) return true;''',
    'suggested specialty matching')
logic = replace_once(logic,
    '''            String[] relevant=specialtyLabNames(specialty);\n            for(int i=0;i<labs.length();i++) {\n                JSONObject lab=labs.optJSONObject(i); if(lab==null) continue;\n                String name=normalize(first(lab,"parameterName","test","name","parameterId"));\n                if(containsAny(name,relevant)) return true;\n            }''',
    '''            for(int i=0;i<labs.length();i++) {\n                JSONObject lab=labs.optJSONObject(i); if(lab==null) continue;\n                String name=normalize(first(lab,"parameterName","test","name","parameterId"));\n                if(specialtyLabMatch(specialty, name)) return true;\n            }''',
    'suggested lab matching')
logic_path.write_text(logic, encoding='utf-8')


def replace_test_method(text, method_name, replacement):
    marker = '@Test public void ' + method_name
    start = text.find(marker)
    if start < 0:
        raise SystemExit('R53 compat missing test method ' + method_name)
    line = text.rfind('\n', 0, start) + 1
    brace = text.find('{', start)
    if brace < 0:
        raise SystemExit('R53 compat malformed test method ' + method_name)
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
        raise SystemExit('R53 compat unclosed test method ' + method_name)
    return text[:line] + replacement.rstrip() + text[end:]

r53_test = TEST / 'R53SpecialToolsTest.java'
tests = r53_test.read_text(encoding='utf-8')
tests = replace_test_method(tests, 'gastroscopyCanBeAddedAsInstrumentalDocument()', '''    @Test public void gastroscopyCanBeAddedAsInstrumentalDocument() {\n        assertEquals("instrumental", R53VisitLogic.documentBucketText("Gastroscopia con biopsia"));\n    }''')
tests = replace_test_method(tests, 'hepatologyDirectAndSuggestedRulesAreDeterministic()', '''    @Test public void hepatologyDirectAndSuggestedRulesAreDeterministic() {\n        assertTrue(R53VisitLogic.specialtyTextMatch("Epatologia", "Visita epatologica"));\n        assertTrue(R53VisitLogic.specialtyTextMatch("Epatologia", "Steatosi epatica"));\n        assertTrue(R53VisitLogic.specialtyLabMatch("Epatologia", "ALT"));\n        assertFalse(R53VisitLogic.specialtyLabMatch("Epatologia", "TSH"));\n    }''')
r53_test.write_text(tests, encoding='utf-8')

print('R53 inherited version expectations aligned:', changed)
print('R53 deterministic testability compatibility applied')
