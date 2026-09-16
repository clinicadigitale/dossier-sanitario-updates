from pathlib import Path
import base64,re,zlib
payload=Path('android-r3/r60_ui_dicom_fixes_payload.py').read_text(encoding='utf-8')
m=re.search(r"b64decode\('([^']+)'\)",payload)
if not m:
    raise SystemExit('R60 compressed payload not found')
code=zlib.decompress(base64.b64decode(m.group(1))).decode('utf-8')
a=code.find('# pressure chart: reserve more bottom and angled dates outside graph')
b=code.find('# vector resources',a)
if a<0 or b<0:
    raise SystemExit('R60 pressure patch markers not found')
pressure="""# pressure chart: reserve more bottom and keep angled dates outside graph
p=pressure_out.read_text()
p=p.replace('float left = dp(50), right = getWidth() - dp(16), top = dp(22), bottom = getHeight() - dp(62);','float left = dp(50), right = getWidth() - dp(16), top = dp(22), bottom = getHeight() - dp(96);')
old='''            String txt = date(day);\n            float w = axis.measureText(txt);\n            float lx=Math.max(left,Math.min(right-dp(6),xx)); canvas.save(); canvas.rotate(-45f,lx,bottom+dp(22)); canvas.drawText(txt,lx,bottom+dp(22),axis); canvas.restore();'''
new='''            String txt = date(day);\n            float lx = Math.max(left + dp(4), Math.min(right - dp(4), xx));\n            canvas.save();\n            canvas.rotate(-45f, lx, bottom + dp(24));\n            axis.setTextAlign(Paint.Align.RIGHT);\n            canvas.drawText(txt, lx, bottom + dp(24), axis);\n            axis.setTextAlign(Paint.Align.LEFT);\n            canvas.restore();'''
if old not in p: raise RuntimeError('pressure dates block missing')
p=p.replace(old,new)
p=p.replace('float ly = getHeight() - dp(14);','float ly = getHeight() - dp(16);')
pressure_out.write_text(p)

"""
code=code[:a]+pressure+code[b:]
exec(compile(code,'android-r3/r60_ui_dicom_fixes_patch.py','exec'))
