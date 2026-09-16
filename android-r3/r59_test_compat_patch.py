from pathlib import Path

TEST = Path('android-r3/app/src/test/java/it/dossiersanitario/clinicadigitale/beta')

# R59 intentionally supersedes the R58 dashboard hero while preserving the same
# navigation/data behavior. Align only the inherited UI identity assertions.
p = TEST / 'R58ModernUiMediaTest.java'
s = p.read_text(encoding='utf-8')
s = s.replace('private void addR58ModernHero()', 'private void addR59ModernHero()')
s = s.replace('addR58ModernHero();', 'addR59ModernHero();')
p.write_text(s, encoding='utf-8')

# R59 modernises the clinical timeline presentation but keeps the R33 clinical-only
# document source. Preserve the semantic regression and allow the new heading.
p = TEST / 'R33ClinicalWeightParityTest.java'
s = p.read_text(encoding='utf-8')
s = s.replace('assertTrue(render.contains("Referti, visite ed esami"));',
              'assertTrue(render.contains("Referti, visite ed esami") || render.contains("Cronologia clinica"));')
p.write_text(s, encoding='utf-8')

print('R59 inherited UI/timeline test compatibility applied')
