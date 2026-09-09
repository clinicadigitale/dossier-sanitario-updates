from pathlib import Path

p = Path('android-r3/app/src/test/java/it/dossiersanitario/clinicadigitale/beta/R31MobileParityTest.java')
s = p.read_text(encoding='utf-8')
s = s.replace('assertTrue(main.contains("syncInteractiveR31"));', 'assertTrue(main.contains("syncInteractiveR39"));')
p.write_text(s, encoding='utf-8')
print('R39 final stale R31 sync assertion aligned')
