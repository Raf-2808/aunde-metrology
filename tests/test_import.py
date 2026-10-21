from openpyxl import Workbook
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker
from backend import obsluga
from backend.modele import Przyrzad, WierszImportu, Wydzial


# Importuje syntetyczny plik, łączy TEST-DUPLIKAT i zachowuje surowe wartości bez nadpisywania późniejszych zmian.
def test_importu_i_idempotencji(baza, monkeypatch, tmp_path):
    monkeypatch.setattr(obsluga, "SesjaBazy", sessionmaker(baza.bind, expire_on_commit=False))
    ksiazka = Workbook()
    s = ksiazka.active
    s.title = "Przyrządy"
    for nr, nazwa in enumerate(obsluga.NAGLOWKI, 1):
        s.cell(4, nr, nazwa)
    s.append(
        [
            1,
            "TEST-DUPLIKAT",
            "Miara",
            "Zwrócona",
            "Nieaktywna",
            "Cutter Wersalska",
            "A",
            "---",
            "2024-01-01",
            12,
            "2025-01-01",
        ]
    )
    s.append(
        [
            2,
            "TEST-DUPLIKAT",
            "Miara",
            "Na stanie",
            "Nieaktywna",
            "Cutter Senatorska",
            "C",
            "---",
            "2025-01-01",
            12,
            "2026-01-01",
        ]
    )
    s.append(
        [
            3,
            "TEST-IMPORT",
            "Waga",
            "Na stanie",
            "Nieaktywna",
            "Laboratorium Kaczeńcowa",
            "Brak grupy",
            "Tak",
            "0000-00-00",
            12,
            None,
        ]
    )
    plik = tmp_path / "test.xlsx"
    raport = tmp_path / "raport.json"
    ksiazka.save(plik)
    proba = obsluga.importuj_excel(str(plik), False, str(raport), {"TEST-DUPLIKAT"})
    assert not proba["zapisano"] and not proba["problemy"]
    assert obsluga.importuj_excel(str(plik), True, str(raport), {"TEST-DUPLIKAT"})["zapisano"]
    rekordy = baza.scalars(select(Przyrzad)).all()
    assert len(rekordy) == 2 and all(r.klasa == "B" for r in rekordy)
    assert len(baza.scalars(select(WierszImportu)).all()) == 3
    assert {w.nazwa for w in baza.scalars(select(Wydzial))} == {
        "Cutter",
        "Laboratorium",
    }
    assert {w.surowe["Grupa"] for w in baza.scalars(select(WierszImportu))} == {
        "A",
        "C",
        "Brak grupy",
    }
    rekordy[0].klasa = "A"
    baza.commit()
    assert obsluga.importuj_excel(str(plik), True, str(raport), {"TEST-DUPLIKAT"})[
        "juz_zaimportowano"
    ]
    baza.expire_all()
    assert baza.get(Przyrzad, rekordy[0].id).klasa == "A"
