from pathlib import Path

P = Path('android-r3/app/src/main/java/it/dossiersanitario/clinicadigitale/beta/R26ChartView.java')
s = P.read_text(encoding='utf-8')

def remove_second_block(text, signature):
    first = text.find(signature)
    if first < 0:
        raise SystemExit('R44 compile fix missing first ' + signature)
    second = text.find(signature, first + len(signature))
    if second < 0:
        return text
    brace = text.find('{', second)
    if brace < 0:
        raise SystemExit('R44 compile fix missing brace ' + signature)
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
        raise SystemExit('R44 compile fix unclosed ' + signature)
    while end < len(text) and text[end] in '\r\n':
        end += 1
    return text[:second] + text[end:]

for sig in [
    '    static float pointXForIndex(int index, int count, float left, float right) {',
    '    static float dateLabelRotationDegrees() {',
    '    private String shortClinicalDate(String raw) {'
]:
    s = remove_second_block(s, sig)

P.write_text(s, encoding='utf-8')
print('R44 duplicate chart helper compile fix applied')
