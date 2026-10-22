# AUNDE Laboratory Management

System badań laboratoryjnych: React/TypeScript/Vite/Tailwind, FastAPI, SQLAlchemy, PostgreSQL, Alembic, ECharts i eksport XLSX. Repozytorium nie zawiera firmowych wyników, tolerancji ani skoroszytu referencyjnego.

## Uruchomienie na VM

1. Skopiuj `.env.example` do `.env`. Ustaw silne hasło PostgreSQL, nazwę DNS i `PUBLIC_URL` zgodne z adresem przeglądarki.
2. Uruchom `docker compose up -d --build`.
3. Utwórz administratora: `docker compose exec backend python -m app.cli create-admin --login admin`. Hasło wprowadza się interaktywnie.
4. Otwórz adres wskazany w `PUBLIC_URL`. Zaufaj certyfikatowi firmowego CA lub CA Caddy zgodnie z instrukcją IT.
5. Dodaj normy, artykuł i konfigurację. Zgłoś lotto i wykonaj badanie. SPC wymaga osobno zatwierdzonego planu.

## Lokalnie w Windows

Uruchom `Start-Lokalnie.ps1` w PowerShell. Skrypt instaluje zależności w `.local`, wykonuje migracje SQLite, prosi o utworzenie administratora i uruchamia API oraz Vite pod `http://127.0.0.1:8080`. Jest to tryb deweloperski dla jednego operatora. Wdrożenie wielostanowiskowe wymaga PostgreSQL przez Compose. Wymagane Python 3.12+, Node 22 i pnpm 11.25; na komputerze Codex skrypt potrafi wykorzystać dostarczony runtime.

## Testy

Backend: `cd backend`, `pip install -r requirements-dev.txt`, `pytest -q`.
Frontend: `cd frontend`, `pnpm install --frozen-lockfile`, `pnpm test`, `pnpm build`.
E2E: `pnpm exec playwright install chromium`, następnie `pnpm test:e2e` przy uruchomionym API. Testy przeglądarkowe nie zastępują odbioru całego procesu.

Pełny test PostgreSQL: ustaw `TEST_DATABASE_URL` na oddzielną bazę testową i uruchom pytest. Testy kasują schemat tej bazy. Nigdy nie wskazuj bazy produkcyjnej. CI używa izolowanej usługi PostgreSQL.

## Dokumentacja

- `EXCEL_ANALYSIS.md`: mapowanie arkuszy i rozbieżności, bez ujawniania danych firmowych.
- `ARCHITECTURE.md`, `DATABASE_SCHEMA.md`, `BUSINESS_RULES.md`: architektura i reguły.
- `DEPLOYMENT.md`: instalacja, aktualizacja, backup i restore.
- `USER_MANUAL_PL.md`: instrukcja użytkownika.
- `VALIDATION.md`: rzeczywisty zakres wykonanej weryfikacji i otwarte elementy odbioru.

Prywatny pakiet lokalny zawiera dodatkowo folder `private/` z pełną analizą komórek i VBA. Folder jest wyłączony z Git. Katalog liczbowy z tego folderu wymaga zatwierdzenia przez właściciela metod, sześć metod jakościowych trzeba skonfigurować po wyjaśnieniu rozbieżności.

## Granice wdrożenia

Kod i testy stanowią implementację do przeglądu. Do uruchomienia produkcyjnego pozostają firmowa VM, DNS/TLS, SMTP i zatwierdzenie metodyki, konfiguracji oraz planu SPC. Nie wykonano połączenia z firmowym SMTP. Domyślnie wysyłka jest wyłączona. Lista braków i ograniczeń funkcjonalnych znajduje się w `VALIDATION.md`.
