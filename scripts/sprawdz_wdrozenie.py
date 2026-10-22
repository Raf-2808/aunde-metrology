"""Kontrola konfiguracji bez uruchamiania usług i bez wypisywania sekretów."""

import argparse
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
from urllib.parse import urlsplit


# Czyta prosty plik KEY=VALUE bez wykonywania kodu; odrzuca niejednoznaczne wpisy.
def wczytaj_konfiguracje(plik: Path) -> dict[str, str]:
    konfiguracja: dict[str, str] = {}
    for numer, linia in enumerate(plik.read_text(encoding="utf-8-sig").splitlines(), 1):
        linia = linia.strip()
        if not linia or linia.startswith("#"):
            continue
        klucz, separator, wartosc = linia.partition("=")
        klucz, wartosc = klucz.strip(), wartosc.strip()
        if not separator or not re.fullmatch(r"[A-Z][A-Z0-9_]*", klucz):
            raise ValueError(f"Niepoprawny wpis konfiguracji w linii {numer}")
        if klucz in konfiguracja:
            raise ValueError(f"Powtórzony klucz konfiguracji w linii {numer}")
        if wartosc.startswith(("'", '"')):
            if len(wartosc) < 2 or wartosc[-1] != wartosc[0]:
                raise ValueError(f"Niedomknięty cudzysłów w linii {numer}")
            wartosc = wartosc[1:-1]
        if "$" in wartosc or "\\" in wartosc:
            raise ValueError(f"Interpolacja lub sekwencja specjalna w linii {numer}")
        konfiguracja[klucz] = wartosc
    return konfiguracja


# Zwraca wyłącznie komunikaty o konfiguracji, nigdy jej wartości ani haseł.
def sprawdz_konfiguracje(konfiguracja: dict[str, str], produkcja: bool) -> list[str]:
    problemy: list[str] = []
    nazwy_hasel = ("OWNER_DB_PASSWORD", "ADMIN_DB_PASSWORD", "PUBLIC_DB_PASSWORD")
    hasla = [konfiguracja.get(nazwa, "") for nazwa in nazwy_hasel]
    for nazwa, haslo in zip(nazwy_hasel, hasla):
        if not re.fullmatch(r"[A-Za-z0-9]{24,}", haslo):
            problemy.append(f"{nazwa}: wymagane co najmniej 24 znaki alfanumeryczne")
    if len(set(hasla)) != len(hasla):
        problemy.append("Hasła trzech ról bazy muszą być różne")
    projekt = konfiguracja.get("COMPOSE_PROJECT_NAME", "")
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", projekt):
        problemy.append("COMPOSE_PROJECT_NAME: wymagana poprawna, jawna nazwa środowiska")
    elif produkcja and re.search(r"(^|[-_])(dev|test)([-_]|$)", projekt):
        problemy.append("COMPOSE_PROJECT_NAME: nazwa DEV/TEST nie pasuje do produkcji")
    porty = [
        konfiguracja.get(nazwa, domyslny)
        for nazwa, domyslny in (("ADMIN_HTTP_PORT", "8080"), ("PUBLIC_HTTP_PORT", "8081"))
    ]
    if any(not p.isascii() or not p.isdigit() or not 1 <= int(p) <= 65535 for p in porty):
        problemy.append("Porty HTTP muszą być liczbami od 1 do 65535")
    if len(set(porty)) != 2 or (
        all(p.isascii() and p.isdigit() for p in porty) and int(porty[0]) == int(porty[1])
    ):
        problemy.append("Porty panelu i karty QR muszą być różne")
    try:
        adres = urlsplit(konfiguracja.get("PUBLIC_BASE_URL", ""))
        poprawny = (
            adres.scheme in ("http", "https")
            and bool(adres.hostname)
            and adres.username is None
            and adres.password is None
            and adres.path in ("", "/")
            and not adres.query
            and not adres.fragment
        )
        adres.port
        if not poprawny:
            raise ValueError()
        if produkcja and (
            adres.scheme != "https" or adres.hostname in ("localhost", "127.0.0.1", "::1")
        ):
            problemy.append("PUBLIC_BASE_URL: produkcja wymaga docelowego hosta HTTPS")
    except ValueError:
        problemy.append(
            "PUBLIC_BASE_URL: wymagany bazowy URL HTTP/HTTPS bez ścieżki i danych logowania"
        )
    for nazwa in ("COOKIE_SECURE", "EMAIL_ENABLED"):
        if konfiguracja.get(nazwa, "") not in ("true", "false"):
            problemy.append(f"{nazwa}: wpisz jawnie true albo false")
    if produkcja and konfiguracja.get("COOKIE_SECURE") != "true":
        problemy.append("COOKIE_SECURE: produkcja wymaga true")
    if konfiguracja.get("EMAIL_ENABLED") == "true":
        if not konfiguracja.get("SMTP_HOST") or not konfiguracja.get("SMTP_FROM"):
            problemy.append("SMTP_HOST i SMTP_FROM są wymagane przy włączonej poczcie")
        port = konfiguracja.get("SMTP_PORT", "587")
        if not re.fullmatch(r"[0-9]{1,5}", port) or not 1 <= int(port) <= 65535:
            problemy.append("SMTP_PORT: wymagany poprawny port serwera STARTTLS")
        if bool(konfiguracja.get("SMTP_USER")) != bool(konfiguracja.get("SMTP_PASSWORD")):
            problemy.append("SMTP_USER i SMTP_PASSWORD muszą być ustawione razem")
    return problemy


# Sprawdza Linux, silnik i składnię Compose; nie buduje, nie uruchamia i nie zmienia usług.
def sprawdz_docker(korzen: Path, plik: Path, konfiguracja: dict[str, str]) -> list[str]:
    if platform.system() != "Linux":
        return ["Odbiór kontenerów wymaga hosta Linux"]
    docker = shutil.which("docker")
    if docker is None:
        return ["Nie znaleziono polecenia docker"]
    for argumenty, opis in (
        (["info", "--format", "{{.OSType}}"], "silnik Docker Linux"),
        (["compose", "version"], "Docker Compose"),
        (["compose", "--env-file", str(plik), "config", "--quiet"], "konfiguracja Compose"),
    ):
        try:
            wynik = subprocess.run(
                [docker, *argumenty],
                cwd=korzen,
                env={**os.environ, **konfiguracja},
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            if wynik.returncode or (argumenty[0] == "info" and wynik.stdout.strip() != "linux"):
                return [
                    f"Nie przeszła kontrola: {opis}. Diagnostykę wykonaj lokalnie, bez publikowania sekretów"
                ]
        except (OSError, subprocess.TimeoutExpired):
            return [f"Nie udało się wykonać kontroli: {opis}"]
    return []


# Wypisuje bezpieczny raport JSON; kod 1 oznacza brak gotowości konfiguracji, bez zmian plików.
def uruchom_kontrole() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", type=Path, default=Path(".env"))
    parser.add_argument("--produkcja", action="store_true")
    parser.add_argument("--docker", action="store_true")
    opcje = parser.parse_args()
    try:
        konfiguracja = wczytaj_konfiguracje(opcje.env)
        # Compose daje pierwszeństwo środowisku procesu nad .env; sprawdzamy te same wartości.
        konfiguracja.update({k: os.environ[k] for k in konfiguracja if k in os.environ})
        problemy = sprawdz_konfiguracje(konfiguracja, opcje.produkcja)
        if opcje.docker and not problemy:
            problemy.extend(
                sprawdz_docker(
                    Path(__file__).resolve().parents[1], opcje.env.resolve(), konfiguracja
                )
            )
    except (OSError, ValueError):
        problemy = [
            "Nie można odczytać konfiguracji. Sprawdź plik i prosty format KEY=VALUE bez duplikatów/interpolacji"
        ]
    print(
        json.dumps(
            {
                "konfiguracja_poprawna": not problemy,
                "problemy": problemy,
                "zakres": "Konfiguracja i opcjonalna kontrola Docker. Bez testu aplikacji, HTTPS, DNS i SMTP",
                "zmieniono_uslugi": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return int(bool(problemy))


if __name__ == "__main__":
    raise SystemExit(uruchom_kontrole())
