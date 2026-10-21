# Wyniki testów i stan odbioru

Data: 21.10.2026. Badana wersja: lokalna wersja testowa projektu, bez wdrożenia produkcyjnego.

## Wykonane kontrole

| Kontrola | Wynik i granice dowodu |
|---|---|
| pytest | 35 testów aplikacji zakończonych powodzeniem. Dodatkowo 11 testów kontroli konfiguracji wdrożenia. Reguły dat, wydziały, filtry, wersje, uprawnienia, archiwum, sesje/CSRF, konta, import, XLSX i QR |
| PostgreSQL 17.11 | Rzeczywista odizolowana baza na 127.0.0.1, poza usługami firmowymi. Test równoległych edycji: jeden zapis, jeden konflikt. Publiczna rola nie czyta R&R, nie zmienia przyrządów i nie usuwa odczytów |
| Migracje od zera | Pełen łańcuch 0001-0003 wykonano także na nowej, pustej bazie PostgreSQL. Powstało 18 tabel, wersja Alembic 0003 |
| Publiczne funkcje DB | Idempotencja odczytu, lista dozwolonych kluczy JSON, brak R&R także przy przekazaniu dodatkowego klucza, unieważnienie tokenu i paginowana historia |
| Playwright Chromium | 4 scenariusze: dodanie/filtrowanie/edycja przydziału i dat/interwału/archiwizacja/przywrócenie; Viewer; zarządzanie kontami; publiczne otwarcie i ponowne otwarcie QR |
| Widok mobilny | Obejrzano kartę przy szerokości 390 px. Nie jest to fizyczny test Android/iOS |
| TypeScript i Vite | Kompilacja typów i produkcyjny build zakończone powodzeniem |
| Eksport | Kolejność A-K, adres z hiperłączem w S, obraz QR w ostatniej kolumnie T z pustą komórką pod obrazem. Test potwierdza rozdzielenie tekstu i obrazu, odczyt QR, R&R w eksporcie Administratora i ochronę przed formułami |
| Dekodowanie QR | ZXing odczytał właściwy URL z osadzonego obrazu i z jego wariantu 160 x 160 px. Nie zastępuje to próby wydruku |
| Import syntetyczny | Próbny i rzeczywisty zapis w izolowanej bazie, połączenie syntetycznego duplikatu z jawnej konfiguracji, B dla wszystkich, wydziały bez ulic, surowe dane zachowane, ponowny import nie nadpisuje późniejszej klasy A |
| Import rzeczywistego źródła | Po zatwierdzeniu sześciu dezaktywacji zapis kopii do oddzielnego lokalnego PostgreSQL: 2134 przyrządy B, 2135 wierszy, 9 wydziałów, sześć Nieaktywna z n/a. Ponowny import nie tworzy duplikatów. Pobranie rejestru: 0,291 s na lokalnym komputerze. Oryginał bez zmian, dane poza repozytorium |
| SMTP | Sprawdzono adres docelowy i deduplikację z atrapą SMTP, bez połączenia z firmowym serwerem i bez wysyłki rzeczywistych wiadomości |
| Backup i restore | pg_dump/pg_restore do nowej testowej bazy. Liczby i SHA-256 zawartości wszystkich 18 tabel były zgodne. Próba dotyczyła syntetycznych danych PostgreSQL, nie produkcji i nie kontenerów |
| Standard kodu | Polskie nazwy logiki i komentarze przed funkcjami, aktualna dokumentacja, pełny rozdział 10A w AGENTS.md, formatowanie Prettier/Ruff. Automatyczna kontrola komentarzy i znaku U+2014 jest uzupełnieniem przeglądu, nie dowodem poprawności treści komentarzy |

Testy nie używały połączenia z produkcyjną bazą, nie zmieniały portalu i nie wysyłały poczty na jakosc@aunde.pl. W plikach testowych znajdują się wyłącznie syntetyczne dane. Logi narzędzi testowych zgłosiły ostrzeżenie deprecacyjne Starlette dotyczące adaptera httpx; nie jest to niepowodzenie testu. Przed aktualizacją zależności ponownie zweryfikować adapter TestClient.

## Pozostałe bramki wdrożenia

1. Import zatwierdzonej kopii na docelowy serwer i kontrola zgodności. Lokalne sprawdzenie importu zakończone.
2. Uruchomienie `docker compose up --build` na czystej Linux VM i kontrola izolacji sieci. Nie ma jeszcze VM, a na komputerze wykonawczym nie było dostępnego Dockera ani WSL; nie deklarujemy uruchomienia kontenerów.
3. Konfiguracja i test firmowego HTTPS, DNS, sieci/VPN, limitów reverse proxy oraz SMTP. EMAIL_ENABLED pozostaje false do akceptacji trybu powiadomień i pierwszego zestawienia historycznych blokad.
4. Fizyczna próba QR na Android/iOS, z monitora i po wydrukowaniu arkusza.
5. Test wydajności na docelowej VM oraz uzgodnienie retencji, RPO/RTO i harmonogramu backupów. Obecny backend filtruje na serwerze po złączeniu danych w pamięci; rozwiązanie wymaga pomiaru dla znacznie większej ewidencji.
6. Weryfikacja wyglądu i reguł zalogowanego portalu. Portal nadal pokazywał formularz logowania, więc zgodność jego mechanizmu edycji nie została potwierdzona.
7. Publikacja kodu w prywatnym repozytorium została zatwierdzona przez właściciela. Dane i sekrety pozostają lokalnie. Produkcja wymaga osobnej autoryzacji użytkownika i IT.

## Podsumowanie etapów

ETAP 1: zaimplementowano aplikację i potwierdzono działanie z lokalnym PostgreSQL i przeglądarką. Start zestawu Docker pozostaje do odbioru na Linux.

ETAP 2: zatwierdzona kopia z sześcioma dezaktywacjami zaimportowana do oddzielnego lokalnego PostgreSQL. Potwierdzono liczby i idempotencję, bez zapisu do produkcji.

ETAP 3: zaimplementowano QR, historię i ograniczoną rolę DB, wykonano testy automatyczne. Fizyczne urządzenia i publiczny HTTPS pozostają do odbioru.

ETAP 4: eksport z osadzonymi QR przeszedł testy struktury i dekodowania. Wydruk pozostaje do sprawdzenia.

ETAP 5: przygotowano Compose, migracje i dokumentację IT, sprawdzono odtworzenie testowej bazy. Nie wykonano wdrożenia produkcyjnego ani testu czystej VM Linux. Projekt nie jest oznaczony jako przyjęty do produkcji.
