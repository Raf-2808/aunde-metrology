"""Kontrole konfiguracji wdrożenia na danych syntetycznych, bez Dockera i sieci."""

import importlib.util
from pathlib import Path
from unittest.mock import patch

import pytest

sciezka = Path(__file__).resolve().parents[1] / "scripts/sprawdz_wdrozenie.py"
specyfikacja = importlib.util.spec_from_file_location("kontrola_wdrozenia", sciezka)
kontrola = importlib.util.module_from_spec(specyfikacja)
specyfikacja.loader.exec_module(kontrola)


# Buduje poprawną syntetyczną konfigurację, bez rzeczywistych sekretów i adresów firmy.
def konfiguracja_testowa() -> dict[str, str]:
    return {
        "OWNER_DB_PASSWORD": "A" * 24,
        "ADMIN_DB_PASSWORD": "B" * 24,
        "PUBLIC_DB_PASSWORD": "C" * 24,
        "COMPOSE_PROJECT_NAME": "metrologia-prod",
        "PUBLIC_BASE_URL": "https://qr.example.invalid",
        "COOKIE_SECURE": "true",
        "EMAIL_ENABLED": "false",
    }


# Potwierdza akceptację konfiguracji oraz wykrycie słabych/identycznych haseł i złych portów.
def test_hasla_i_porty() -> None:
    konfiguracja = konfiguracja_testowa()
    assert kontrola.sprawdz_konfiguracje(konfiguracja, True) == []
    konfiguracja.update(ADMIN_DB_PASSWORD="A" * 24, PUBLIC_DB_PASSWORD="sekret")
    konfiguracja.update(ADMIN_HTTP_PORT="08080", PUBLIC_HTTP_PORT="8080")
    problemy = kontrola.sprawdz_konfiguracje(konfiguracja, True)
    assert len(problemy) == 3
    assert all("sekret" not in p and "A" * 24 not in p for p in problemy)


# Odrzuca błędne lub lokalne adresy QR i produkcyjne cookies bez HTTPS.
@pytest.mark.parametrize(
    "adres",
    [
        "http://qr.example.invalid",
        "https://localhost",
        "https://[::1]",
        "https://u:p@host",
        "https://host/p/token",
        "https://host:bledny",
    ],
)
def test_produkcyjny_adres_qr(adres: str) -> None:
    konfiguracja = konfiguracja_testowa()
    konfiguracja.update(PUBLIC_BASE_URL=adres, COOKIE_SECURE="false")
    problemy = kontrola.sprawdz_konfiguracje(konfiguracja, True)
    assert len(problemy) == 2


# Blokuje niepełne ustawienia poczty i nazwę testową w trybie produkcyjnym.
def test_smtp_i_srodowisko() -> None:
    konfiguracja = konfiguracja_testowa()
    konfiguracja.update(
        EMAIL_ENABLED="true",
        SMTP_USER="konto",
        SMTP_PORT="0",
        COMPOSE_PROJECT_NAME="metrologia-test",
    )
    assert len(kontrola.sprawdz_konfiguracje(konfiguracja, True)) == 4


# Czyta BOM i cudzysłowy bez wykonywania podstawień oraz blokuje duplikaty i interpolację.
def test_odczyt_env(tmp_path: Path) -> None:
    plik = tmp_path / "test.env"
    plik.write_text('\ufeff# komentarz\nKLUCZ="wartosc"\nPUSTE=\n', encoding="utf-8")
    assert kontrola.wczytaj_konfiguracje(plik) == {"KLUCZ": "wartosc", "PUSTE": ""}
    for tresc in ("X=1\nX=2", "X=${INNY}", 'X="brak', "niepoprawny wpis"):
        plik.write_text(tresc, encoding="utf-8")
        with pytest.raises(ValueError):
            kontrola.wczytaj_konfiguracje(plik)


# Weryfikuje, że Windows nie jest uznawany za dowód odbioru na Linuxie.
def test_docker_wymaga_linux() -> None:
    with patch.object(kontrola.platform, "system", return_value="Windows"):
        assert kontrola.sprawdz_docker(Path("."), Path("test.env"), {}) == [
            "Odbiór kontenerów wymaga hosta Linux"
        ]


# Wyjście Docker może zawierać sekret; kontrola zwraca tylko ogólny błąd i nie uruchamia usług.
def test_blad_docker_bez_ujawnienia_sekretu() -> None:
    with (
        patch.object(kontrola.platform, "system", return_value="Linux"),
        patch.object(kontrola.shutil, "which", return_value="/usr/bin/docker"),
        patch.object(kontrola.subprocess, "run") as wykonaj,
    ):
        wykonaj.return_value.returncode = 1
        wykonaj.return_value.stderr = "NIE_UJAWNIAJ"
        problemy = kontrola.sprawdz_docker(Path("."), Path("test.env"), {})
        assert "NIE_UJAWNIAJ" not in str(problemy)
        assert wykonaj.call_count == 1
        assert wykonaj.call_args.args[0][1] == "info"
