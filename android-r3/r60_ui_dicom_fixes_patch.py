from pathlib import Path
p=Path('android-r3/r60_ui_dicom_fixes_payload.py')
s=p.read_text(encoding='utf-8')
bad="'),'utf-8'),'android-r3/r60_ui_dicom_fixes_patch.py','exec'))"
good="')).decode('utf-8'),'android-r3/r60_ui_dicom_fixes_patch.py','exec'))"
if bad not in s:
    raise SystemExit('R60 payload wrapper pattern not found')
s=s.replace(bad,good,1)
exec(compile(s,'android-r3/r60_ui_dicom_fixes_payload.py','exec'))
