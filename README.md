# AUNDE Metrologia

Aplikacja do ewidencji przyrządów z lokalnymi kontami, rolami, PostgreSQL, publiczną kartą QR i eksportem XLSX. React i FastAPI zapisują dane w bazie; interfejs nie używa zastępczej ewidencji w pamięci przeglądarki.

## Szybkie uruchomienie DEV

Wymagane na Linux VM: Docker Engine z poleceniem `docker compose`. Na VM nie trzeba instalować Python, Node.js ani PostgreSQL.

1. Skopiuj `.env.example` do `.env`. Ustaw trzy różne losowe hasła alfanumeryczne, każde co najmniej 24 znaki. Nie dodawaj `.env` do Git.
2. Ustaw `PUBLIC_BASE_URL` na adres dostępny z urządzeń skanujących. `localhost` nadaje się tylko do testów na tym samym komputerze.
3. Uruchom:

```sh
docker compose up --build -d
docker compose ps -a
docker compose exec api python -m backend.obsluga administrator administrator
```

Ostatnie polecenie poprosi o hasło, bez przekazywania go w argumentach procesu. Zaloguj się na `http://localhost:8080`. Publiczny host testowy: `http://localhost:8081/p/TOKEN`, przy czym token generuje aplikacja i umieszcza w eksporcie XLSX.

Baza, backendy i rola migracyjna nie są wystawiane na portach hosta. Porty Nginx są przypięte do 127.0.0.1. Firmowy reverse proxy powinien mieć dostęp do tych portów lokalnie. Szczegóły HTTPS, sieci i publikacji w `docs/WDROZENIE.md`.

## Praca z rejestrem

Kliknij nagłówek kolumny, aby wybrać wiele wartości, puste komórki, zakres lub sortowanie. Podpowiedzi obejmują rekordy ze wszystkich stron pasujące do filtrów innych kolumn. Komórki edytujesz po kliknięciu, zapis następuje po Enter lub opuszczeniu pola. Daty mają kalendarz. Konflikt wersji wymaga odświeżenia, zamiast nadpisania cudzej edycji.

Nowy przyrząd ma grupę B, status Nieaktywna, stan techniczny Nieustalony i komentarz dat `n/a`. Przydziałem jest wydział bez ulicy. Nie aktywuj przyrządu bez poprawnych dat. Nowy przyrząd ma ręczną blokadę. Import ustawia aktywnym Odblokowany, pozostałym Zablokowany. Kliknięcie komórki Blokada pozwala Editorowi i Administratorowi zmienić to ustawienie. Pozytywny wynik czynności nie jest warunkiem odblokowania.

Grupa A wybiera wzorcowanie, B sprawdzenie, C brak obowiązkowego procesu okresowego. Zmiana grupy wymaga uzasadnienia i zachowuje historię. Przekroczony wymagany termin blokuje użytkowanie niezależnie od ręcznego Status. Automatycznie blokuje także stan Niesprawny. Zmiana na Sprawny usuwa tę przyczynę, ale nie znosi przekroczonego terminu ani blokady ręcznej. Nieustalony stan i brak/negatywny wynik nie blokują automatycznie. Korekta daty nie zastępuje rejestracji rzeczywistej czynności.

Administrator dodaje przyrządy i konta, eksportuje R&R, archiwizuje/przywraca, nadpisuje termin z uzasadnieniem i rotuje token QR. Editor edytuje pola biznesowe i rejestruje czynności, Viewer przegląda i filtruje. Publiczna karta nie ma przycisków edycji ani potwierdzania sprawdzenia.

## Import źródła

Oryginalny Excel i instrukcja firmowa nie są częścią repozytorium. Próbny import nie zapisuje do bazy. Dostęp do pliku należy nadać jawnie przez montowanie katalogu, np.:

```sh
docker compose run --rm -v /bezpieczne/dane:/dane api python -m backend.obsluga import /dane/ewidencja.xlsx --raport /dane/raport-importu.json --konfiguracja /dane/scalenia.json
```

Po rozwiązaniu błędów na roboczej kopii pliku dodaj `--zapisz`. Pierwszy import wymaga pustej ewidencji. Ten sam SHA-256 nie tworzy kolejnej partii. Inna wersja pliku po pierwszym imporcie wymaga uzgodnienia UUID i nie nadpisuje zmian w aplikacji.

Numery z jawnej konfiguracji `scalenia.json` są scalane do jednego przyrządu z bieżącym nowszym wpisem. Konfiguracja ma postać `{"polacz_numery":["NUMER_ZATWIERDZONY_PRZEZ_WLASCICIELA"]}` i pozostaje poza repozytorium. Bez niej każdy duplikat wstrzymuje zapis. Obydwa źródłowe wiersze są zachowane. Każdy przyrząd otrzymuje B, także źródłowe A/C. Nazwy wydziałów tracą dopisek Wersalska/Senatorska/Kaczeńcowa. Brakujące i przyszłe daty Ostatni są dopuszczalne tylko dla nieaktywnych z komentarzem `n/a`. Źródłowy plik zawiera sześć aktywnych wyjątków. Właściciel zatwierdził ich dezaktywację na kopii importowej, którą zapisano do odizolowanej lokalnej bazy z komentarzem n/a. Import na docelowy serwer pozostaje do wykonania. Oryginał zachowuje błędne daty, więc jego bezpośredni import nadal jest wstrzymywany. Nie ma automatycznej dezaktywacji ani cichego pomijania tych rekordów.

## Powiadomienia

Adres docelowy alertów: `jakosc@aunde.pl`. Domyślnie `EMAIL_ENABLED=false`. Wysyłkę włącz dopiero po uzgodnieniu trybu i konfiguracji SMTP z IT, sprawdzeniu rejestru oraz próbie na serwerze testowym. Obecna implementacja kolejkuje jeden alert dla przyrządu/procesu/przekroczonego terminu, ponawia błędy i nie wysyła ponownie po udanym zapisie wysyłki. Po awarii po przyjęciu SMTP przed COMMIT możliwy jest powtórzony e-mail. Blokada działa także przy wyłączonej lub uszkodzonej poczcie. Kontrola terminów odbywa się co 60 sekund, niezależnie od wejść na stronę. Na pierwsze uruchomienie z danymi historycznymi trzeba uzgodnić sposób zestawienia istniejących blokad; nie włączać wtedy wysyłki w ciemno.

## Testy i aktualny stan

```sh
# W katalogu projektu, z zależnościami requirements.txt:
pytest -q
# Z oddzielną bazą testową o nazwie zawierającej test:
TEST_DATABASE_URL=... TEST_PUBLIC_DATABASE_URL=... pytest -q
# W frontend/:
pnpm install --frozen-lockfile
pnpm build
pnpm exec playwright install chromium
TEST_LOGIN_PASSWORD=... TEST_QR_TOKEN=... pnpm test:e2e
```

Testy E2E wymagają uruchomionej aplikacji, syntetycznych kont `test-administrator` i `test-viewer` oraz testowego przyrządu z aktywnym QR. Nie uruchamiaj ich na produkcji. Szczegółowe wyniki i bramki wdrożenia są w `docs/WYNIKI_TESTOW.md`.

Dokumentacja funkcji: `docs/DOKUMENTACJA_FUNKCJI.md`. Model i mapowanie: `docs/MODEL_DANYCH.md`. Instalacja, aktualizacja i backup/restore: `docs/WDROZENIE.md`. Reguły obowiązujące kolejne prace: pełny rozdział 10A w `AGENTS.md`.

Nie wykonano wdrożenia produkcyjnego ani publikacji danych w GitHub. Właściciel zatwierdził publikację kodu w prywatnym repozytorium Raf-2808/aunde-metrology. Dane importu i sekrety pozostają poza GitHub.
