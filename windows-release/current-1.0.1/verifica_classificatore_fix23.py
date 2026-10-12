#!/usr/bin/env python3
"""Regression suite FIX23 per il classificatore documentale.

Uso:
    python verifica_classificatore_fix23.py <cartella_backup_dossier>

Il test usa esclusivamente il testo OCR gia' presente negli indici del backup.
Non apre gli originali e non rilancia l'OCR.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ENGINE_DIR = Path(__file__).resolve().parents[1] / "python_engine"
sys.path.insert(0, str(ENGINE_DIR))
import dossier_engine as engine  # noqa: E402

# file, documentKind atteso, specializzazione attesa, data attesa opzionale
CASES = [
    ("03_Dermatologo_25_02_26_ocr.pdf", "Visita dermatologica", "Dermatologia", "2016-02-25"),
    ("esame_audiometrico_cordoni_24012023_ocred.pdf", "Visita ORL con esame audiometrico", "Otorinolaringoiatria", "2023-01-24"),
    ("visita_troyer_06042023_ocred.pdf", "Visita specialistica lipolinfedema", "Linfologia/Angiologia", "2023-04-06"),
    ("visita_cardiologica_+_ECG_21022025_ocr.pdf", "Visita cardiologica con ECG", "Cardiologia", "2025-02-21"),
    ("emogas_23062023_ocr.pdf", "Visita pneumologica con emogasanalisi", "Pneumologia", "2023-06-23"),
    ("visita_pneumologica_31082023_ocr.pdf", "Visita pneumologica", "Pneumologia", "2023-08-31"),
    ("visita_pneumologica_+_emogas_20032024_ocr.pdf", "Visita pneumologica con emogasanalisi", "Pneumologia", "2024-03-20"),
    ("ecodoppler_arti_inferiori_18102023_ocr.pdf", "Ecocolordoppler arti inferiori", "Angiologia/Radiologia", "2023-10-18"),
    ("confronto analisi GA - 11_2024.pdf", "Confronto analisi", "Laboratorio analisi", "2023-03-25"),
    ("visita_cardiologica_20032024_ocr.pdf", "Visita cardiologica con ECG", "Cardiologia", "2024-03-20"),
    ("visita_cardiologica_+_ECG_26102023_ocr.pdf", "Visita cardiologica con ECG", "Cardiologia", "2023-10-26"),
    ("visita_diabetologica_18042024_ocr.pdf", "Visita diabetologica", "Diabetologia", "2024-04-18"),
    ("visita_diabetologica_29092023_ocr.pdf", "Visita diabetologica", "Diabetologia", "2023-09-29"),
    ("visita_diabetologica_27-10-2025_ocr.pdf", "Visita diabetologica", "Diabetologia", "2025-10-27"),
    ("03a_Visita_endocrina_21_09_2021_ocred.pdf", "Visita endocrinologica", "Endocrinologia", "2021-09-21"),
    ("Gastroscopia_05-11-2025_ocr.pdf", "Gastroscopia", "Gastroenterologia", "2025-11-05"),
    ("esame_istologico_16022023_ocr.pdf", "Anatomia patologica", "Anatomia patologica", "2023-02-16"),
    ("polisonnografia_20072023_ocr.pdf", "Saturimetria notturna", "Pneumologia", "2023-07-20"),
    ("ecodoppler_cardiaco_20052024_ocr.pdf", "Ecocardiogramma", "Cardiologia", "2024-05-20"),
    ("ecodoppler_tronchi_sovraortici_25102023_ocr.pdf", "Ecocolordoppler TSA", "Angiologia/Radiologia", "2023-10-25"),
    ("mammografia_vanna_16012019.pdf", "Mammografia con ecografia mammaria", "Senologia/Radiologia", "2019-01-16"),
    ("referto_visita_reumatologica_vanna_07122021.pdf", "Visita reumatologica", "Reumatologia", "2021-12-07"),
    ("06_visita cardiologica_09042026_ocr.pdf", "Visita cardiologica", "Cardiologia", "2026-04-09"),
    ("09_visita_neurologica_DA_23062026_ocr.pdf", "Visita neurologica", "Neurologia", "2026-06-23"),
    ("11_visita_diabetologica_DA_10072026_ocr.pdf", "Visita diabetologica", "Diabetologia", "2026-07-10"),
    ("sangue_occulto_03032025.pdf", "Ricerca sangue occulto nelle feci", "Screening colon-retto", "2025-03-03"),
    ("08_referto_OSAS_15062026_ocr.pdf", "Monitoraggio terapia CPAP", "Pneumologia/Medicina del sonno", "2026-06-15"),
    ("paptest_vanna_04092019.pdf", "Pap test", "Ginecologia", "2019-09-04"),
    ("Immagine 2026-07-30 215557.png", "Terapie farmacologiche in corso", "", ""),
    ("tactorace_vanna_16032026.pdf", "TAC", "Radiologia", "2026-03-16"),
]

SYNTHETIC = [
    (
        "specialita_non_in_ontologia",
        "Prestazione 89.7 VISITA ALLERGOLOGICA\nAnamnesi: rinite.\nDiagnosi: sospetta allergia.\nTerapia: antistaminico.\nData visita: 12/08/2026",
        "Visita allergologica",
        "Allergologia",
        "2026-08-12",
    ),
    (
        "specialista_non_in_ontologia",
        "Dr. Test\nMEDICO CHIRURGO\nSPECIALISTA IN ALLERGOLOGIA E IMMUNOLOGIA\nPaziente: Test\nDiagnosi: rinite allergica\nPrescrizione: terapia\n12/08/2026",
        "Visita specialistica di Allergologia e immunologia",
        "Allergologia e immunologia",
        "",
    ),
    (
        "esame_non_in_ontologia",
        "Azienda sanitaria\nTipo Esame: Densitometria ossea femorale\nData Esame: 11/08/2026\nTesto Referto\nRisultato nei limiti",
        "Densitometria ossea femorale",
        "",
        "2026-08-11",
    ),
]


def load_documents(root: Path) -> dict[str, dict]:
    result: dict[str, dict] = {}
    for index in root.rglob("indice_documenti.json"):
        data = json.loads(index.read_text(encoding="utf-8"))
        docs = data if isinstance(data, list) else data.get("documents", data.get("items", []))
        for doc in docs or []:
            name = str(doc.get("originalName") or "")
            if name:
                result[name] = doc
    return result


def classify(doc: dict, name: str) -> dict:
    # Per il test del classificatore non si rilancia OCR: si usa il testo gia' estratto.
    return engine.analyze_document_v420({"text": doc.get("extractedText") or "", "pages": []}, name)


def main() -> int:
    if len(sys.argv) != 2:
        print("Uso: python verifica_classificatore_fix23.py <cartella_backup_dossier>")
        return 2
    root = Path(sys.argv[1]).resolve()
    if not root.exists():
        print(f"Backup non trovato: {root}")
        return 2
    docs = load_documents(root)
    print(f"Documenti indicizzati trovati: {len(docs)}")
    failed = 0
    passed = 0
    for name, expected_kind, expected_spec, expected_date in CASES:
        doc = docs.get(name)
        if not doc:
            print(f"[FAIL] {name}: documento non trovato")
            failed += 1
            continue
        out = classify(doc, name)
        got = (out.get("documentKind") or "", out.get("specialization") or "", out.get("clinicalDate") or "")
        exp = (expected_kind, expected_spec, expected_date)
        checks = [got[0] == exp[0], got[1] == exp[1]]
        if expected_date:
            checks.append(got[2] == expected_date)
        if all(checks):
            print(f"[PASS] {name} -> {out.get('title')}")
            passed += 1
        else:
            print(f"[FAIL] {name}")
            print(f"       atteso: {exp}")
            print(f"       ottenuto: {got} | titolo={out.get('title')!r}")
            failed += 1

    print("\nTest strutturali sintetici, senza parole chiave preconfigurate:")
    for name, text, expected_kind, expected_spec, expected_date in SYNTHETIC:
        out = engine.analyze_document_v420({"text": text, "pages": []}, f"{name}.pdf")
        got = (out.get("documentKind") or "", out.get("specialization") or "", out.get("clinicalDate") or "")
        checks = [got[0] == expected_kind, got[1] == expected_spec]
        if expected_date:
            checks.append(got[2] == expected_date)
        if all(checks):
            print(f"[PASS] {name} -> {out.get('title')}")
            passed += 1
        else:
            print(f"[FAIL] {name}: {got} | titolo={out.get('title')!r}")
            failed += 1

    print(f"\nRISULTATO: {passed} PASS, {failed} FAIL")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
