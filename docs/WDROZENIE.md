# Instalacja aktualizacja i utrzymanie

## Środowiska

Oddziel DEV/TEST i PROD przez osobne katalogi, `.env`, wartości COMPOSE_PROJECT_NAME, porty, wolumeny i hasła. Nie używaj testów E2E na produkcji. Wymagany Docker Engine i Compose na Linux VM. Obrazy budują Python/Node wewnątrz kontenerów.

Nie zmieniaj nazwy projektu Compose po utworzeniu danych bez świadomego wskazania istniejącego wolumenu. Polecenie `docker compose down -v` usuwa bazę i nie należy do procedury aktualizacji.

## Instalacja

Przed startem uruchom `python3 scripts/sprawdz_wdrozenie.py --env .env --docker`. Dla produkcji dodaj `--produkcja`. Kontrola uwzględnia pierwszeństwo zmiennych środowiska, sprawdza różne hasła ról, porty, bazowy URL, cookies i kompletność SMTP. Opcja Docker sprawdza host Linux, silnik oraz `docker compose config --quiet`. Raport JSON nie zawiera wartości konfiguracji. Polecenie nie buduje obrazów, nie uruchamia usług ani migracji. Poprawny raport nie potwierdza działania HTTPS, DNS, SMTP ani aplikacji. Dla tej kontroli potrzeba Python 3.10+ na hoście; pozostała instalacja korzysta z kontenerów.

Skopiuj `.env.example` do `.env`, ustaw losowe sekrety i `chmod 600 .env`. Hasła DB wyłącznie alfanumeryczne, min. 24 znaki, aby bezpiecznie używać ich w URL połączenia i kontrolowanym provisioningu ról. Oddzielne hasła właściciela, administracyjnej aplikacji i publicznej aplikacji. Nigdy nie używaj właściciela schematu do obsługi żądań HTTP.

`docker compose up --build -d` uruchamia PostgreSQL, czeka na zdrowie, wykonuje migracje Alembic i provisioning ról, następnie backendy i Nginx. Niepowodzenie migracji blokuje aplikację. Sprawdź `docker compose ps -a`, logi migracji i healthcheck. Nie ma automatycznego tworzenia tabel przy starcie API.

Utwórz pierwsze konto poleceniem `docker compose exec api python -m backend.obsluga administrator administrator`. Hasło wprowadzane interaktywnie, min. 12 znaków, haszowane Argon2id. Kolejne konta dodaje Administrator z panelu. Zachowaj co najmniej jednego aktywnego Administratora.

## Reverse proxy i HTTPS

Admin HTTP: 127.0.0.1:8080, QR HTTP: 127.0.0.1:8081. Wystaw publiczny host HTTPS tylko na port QR, a administracyjny host HTTPS tylko w sieci firmowej/VPN na port admin. Nginx portu QR nie przekazuje `/api/`. Ograniczenia muszą istnieć również w firewallu i firmowym reverse proxy.

Ustaw PUBLIC_BASE_URL na docelowy adres HTTPS QR przed eksportem kodów. W PROD ustaw COOKIE_SECURE=true. Certyfikaty i klucze pozostają w zarządzanym przez IT proxy, poza repozytorium. Dla lokalnego DEV HTTP COOKIE_SECURE=false jest konieczne do testowania cookie.

Nginx ogranicza logowania i żądania QR. Za firmowym proxy adres źródłowy w kontenerze może być wspólny. IT powinno ustawić limity także na firmowym proxy według rzeczywistego adresu klienta i dostosować burst do NAT. Nie ufaj dowolnemu X-Forwarded-For z Internetu. Aplikacja nie loguje ścieżek zawierających token; zewnętrzne proxy musi mieć tę samą politykę.

## Migracja ewidencji

Uruchom próbny importer z README na odczytywanej kopii pliku w bezpiecznym katalogu. Zachowaj oryginał, raport i SHA-256. Właściciel zatwierdził dezaktywację sześciu wyjątków dat na kopii importowej. Kopię zaimportowano i zweryfikowano w odizolowanym lokalnym PostgreSQL. Sześć pozycji ma Nieaktywna i komentarz n/a. Import na serwer pozostaje do wykonania. Zapis jest atomowy i wymaga pustej ewidencji. Po imporcie sprawdź 2134 przyrządy, 2135 surowych wierszy, B dla wszystkich oraz 9 wydziałów. Uzgodniony duplikat ma jeden UUID, źródłowe oznaczenia A/C i ulice pozostają w chronionym materiale importu.

Nie nadpisuj bieżących edycji po samym Numer. Obsługa kolejnego, zmienionego pliku wymaga osobnej procedury uzgodnienia UUID. Odczyt źródła nie tworzy pozytywnych wyników czynności ani sprawności.

Zatwierdzone numery do połączenia umieść w lokalnym JSON z listą `polacz_numery` i przekaż przez `--konfiguracja /dane/scalenia.json`. Plik pozostaje poza repozytorium. Bez konfiguracji duplikaty wstrzymują import. Do projektu dołączono oddzielny lokalny plik konfiguracyjny użytkownika, którego nie należy kopiować do GitHub.

## SMTP

Wysyłka jest wyłączona domyślnie. Wprowadź SMTP_HOST, SMTP_PORT, SMTP_FROM i opcjonalnie SMTP_USER/SMTP_PASSWORD poza repozytorium. Klient wymaga STARTTLS ze sprawdzeniem certyfikatu. Nie obniżaj ochrony TLS dla obejścia błędu. Jeżeli firmowy serwer wymaga innego uwierzytelniania, przygotuj zatwierdzoną konfigurację przed włączeniem.

Próba poczty odbywa się na testowym SMTP bez produkcyjnych adresatów. Po akceptacji sposobu alertów ustaw EMAIL_ENABLED=true i odtwórz proces `powiadomienia`. Obecna reguła to jeden e-mail do jakosc@aunde.pl dla nowego przekroczonego terminu aktywnego przyrządu. Pierwsze uruchomienie z historią może wygenerować wiele alertów; potrzebna decyzja o zestawieniu początkowym. Nie włączaj wysyłki przed tą decyzją.

## Backup

W katalogu projektu uruchom `bash scripts/backup.sh /bezpieczne/backupy`. Plik custom-format tworzy pg_dump z kontenera i sprawdza odczyt katalogu backupu. To nie zastępuje odtworzenia. Harmonogram ustala IT, z retencją i RPO/RTO zgodnymi z polityką firmy. Trzymaj zaszyfrowaną kopię poza VM; backup zawiera R&R, historię i publiczne tokeny. Zachowaj bezpiecznie także `.env`, konfigurację proxy i wersję kodu. Nie dodawaj tych danych do GitHub.

## Odtworzenie próbne

`bash scripts/odtworz-testowo.sh /bezpieczne/backup.dump metrologia_restore_proba` tworzy nową bazę i nie zastępuje aktywnej. Błąd istniejącej nazwy przerywa wykonanie. Sprawdź liczby rekordów i historii, tokeny, poprawność FK i prawa publicznej roli. Dla pełnego testu skieruj oddzielny projekt TEST na odtworzoną bazę, przy wyłączonej poczcie i odizolowanej sieci.

Odtworzenie produkcji wymaga osobnego zatwierdzenia, okna serwisowego i udokumentowanego wyboru backupu. Skrypty nie przełączają samodzielnie produkcyjnego połączenia i nie usuwają istniejącej bazy. Role są zasobem klastra: przed odtworzeniem na nowym klastrze wykonaj provisioning z tymi samymi nazwami ról i nowymi bezpiecznymi hasłami.

## Aktualizacja

1. Zapisz wersję kodu/obrazów i wykonaj backup z próbą odtworzenia.
2. Zweryfikuj nową wersję na DEV/TEST i przeczytaj migracje.
3. W zatwierdzonym oknie zatrzymaj ruch i kontenery API, publiczne i powiadomienia, pozostawiając bazę.
4. Zbuduj obrazy, uruchom jednorazowo migracje, sprawdź wynik, uruchom całość i testy kontrolne.
5. Po akceptacji przywróć ruch. Nie wykonuj automatycznego downgrade po błędzie. Cofnięcie kodu wymaga zgodnego schematu, a czasem zatwierdzonego odtworzenia kopii bazy.

Polecenia po akceptacji: `docker compose build`, `docker compose run --rm migracje`, `docker compose up -d`. Nie używaj `docker compose down -v`. Zmiana hasła w `.env` nie zmienia automatycznie hasła istniejącego właściciela PostgreSQL; rotację wykonuje IT osobno.

## Diagnostyka

Sprawdzaj healthcheck, wynik migracji, wolne miejsce, połączenia bazy i kolejkę `powiadomienia_email` jako Administrator IT. Logi backendu zawierają identyfikator zdarzenia i typ błędu, bez sekretów. Uvicorn i Nginx mają wyłączone logi URL. Nie udostępniaj stacktrace z parametrami poza zespół IT.

Weryfikacja na czystej VM Linux, HTTPS, firewallu i firmowego SMTP jest obowiązkową częścią odbioru wdrożenia. Test lokalnego PostgreSQL na Windows tego nie zastępuje.
