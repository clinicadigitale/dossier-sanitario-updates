from pathlib import Path

source_path = Path('android-r3/r23_login_iv_fix_patch.py')
source = source_path.read_text(encoding='utf-8')
start = source.find("    old_oncreate = r'''")
end = source.find("    marker = '    private View buildUi() {\\n'", start)
if start < 0 or end < 0:
    raise SystemExit('R23 v2 patch failed: startup replacement block not found')
replacement = '''    s = replace_once(\n        s,\n        '        setContentView(buildUi());\\n        String initial = state == null ? "Panoramica" : state.getString("current_section", "Panoramica");\\n        renderSection(initial);\\n',\n        '        showStartupGate(state);\\n',\n        'startup gate onCreate'\n    )\n\n'''
source = source[:start] + replacement + source[end:]
exec(compile(source, str(source_path), 'exec'), {'__name__': '__main__'})
