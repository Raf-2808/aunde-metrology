# Weryfikacja i odbiór

Stan lokalny: 22.10.2026. Wyniki poniżej dotyczą faktycznie wykonanych poleceń, nie deklaracji gotowości infrastruktury.

## Wykonano

- Statyczny odczyt wszystkich pięciu arkuszy, ukrytej matrycy, nazwanych zakresów, komórek, formuł, cache i źródeł VBA. Źródła nie zapisano i makr nie uruchamiano.
- Migracja Alembic `001` na świeżej bazie SQLite i inicjalizacja neutralnych danych QA.
- pytest: 25 testów zaliczonych, 1 test równoległych transakcji PostgreSQL pominięty lokalnie z powodu braku PostgreSQL. Test jest skonfigurowany do wykonania w CI.
- Vitest: 3 testy zaliczone. TypeScript: kompilacja bez błędów.
- Vite: produkcyjny build zakończony. ECharts daje ostrzeżenie o rozmiarze pakietu, bez błędu budowania.
- API: testy wszystkich 13 grup kryteriów akceptacyjnych, rozszerzone o stare plany, niezmienność konfiguracji, korekty, CSRF, Origin i wygasanie scope.
- Eksport: odczyt wygenerowanych XLSX przez openpyxl potwierdził wartości, czerwone wypełnienia i brak dopisku NOK do wartości pomiarów.
- Przeglądarka lokalna: logowanie, widok kolejki, uruchomienie formularza, nieaktywny zapis przy brakach, czerwony pojedynczy pomiar ze zgodną średnią, wymagane potwierdzenie, zatwierdzony zapis, status partii ZBADANE oraz odblokowanie wyników rzeczywistych hasłem. Wizualnie sprawdzono kolejkę i formularz przy szerokości 1600 px.
- GitHub Actions dla commitu `581b1157b6a27a64838ee02f7d7e91d4eb5876c3`: zadania backend i frontend zakończyły się sukcesem. Obejmuje to migrację i 26 testów na PostgreSQL, w tym równoległy zapis, oraz Playwright. [Wynik CI](https://github.com/Raf-2808/aunde-metrology/actions/runs/39758295084).
- GitHub Actions dla commitu `536a6dfcee037b55f10c09308e58f1927952c1af`: wszystkie trzy zadania zakończyły się sukcesem, w tym budowa i uruchomienie pełnego Docker Compose na Linux, zaufane HTTPS przez CA Caddy, healthcheck API i utworzenie pliku backupu. [Wynik Compose i testów](https://github.com/Raf-2808/aunde-metrology/actions/runs/39758677856).

## Mapowanie etapów

| Etap | Dowód weryfikacji |
|---|---|
| 1. Excel | Pełna mapa i statyczna analiza VBA w prywatnym pakiecie |
| 2. Baza i normy | Migracja lokalna; testy tworzą schemat i katalog |
| 3. Konfiguracja | Walidacja 1..10 punktów i test zachowania historycznej wersji |
| 4. Formularz | Testy średniej, NOK, kompletności i potwierdzenia; próba w przeglądarce |
| 5. Harmonogram i lotto | Test dziesiątego cyklu, kilku sesji, wstrzymania i starego planu |
| 6. Rzeczywiste i Recover | Test odczytu oddzielnych sesji i kontroli uprawnień |
| 7. Symulacja | Test przekształcenia pojedynczych pomiarów, średniej i braku zmiany źródła |
| 8. SPC i SMTP | Test współczynników, I-MR, alarmu, outbox i deduplikacji; bez faktycznej wysyłki |
| 9. Bezpieczeństwo i eksport | Role, osobne scopes, expiry, CSRF, Origin i odczyt eksportu XLSX |
| 10. Wdrożenie | Pełny Compose, HTTPS/API i utworzenie backupu przeszły CI na Linux; pozostaje firmowa VM i restore |

Testy etapów 2..9 uruchomiono łącznie po implementacji. Nie deklarujemy osobnego pełnego odbioru na końcu każdego etapu historycznego.

## Pozostały odbiór techniczny

1. Odbiór Compose na docelowej firmowej VM. PostgreSQL, współbieżność oraz budowa i uruchomienie pełnego Compose przeszły CI na Linux. Lokalnie Docker nie był dostępny.
2. DNS, certyfikat firmowy/CA Caddy, reguły proxy i kontrola dostępu sieciowego.
3. Test firmowego SMTP, rejestr Message-ID, odbiorcy oraz procedura obsługi UNCERTAIN/SENDING. Niczego nie wysyłano.
4. Faktyczny backup i próbny restore na oddzielnej VM. Skrypt i instrukcja nie są dowodem udanego odtworzenia.
5. Odbiór ról i metod przez laboratorium, potwierdzenie sześciu niejednoznacznych charakterystyk jakościowych i planu próbkowania SPC.
6. Dłuższy test obciążeniowy, przegląd bezpieczeństwa zależności oraz test pełnego interfejsu na małym ekranie. Lokalna próba przeglądarkowa nie pokrywa wszystkich formularzy.

## Ograniczenia funkcjonalne do decyzji właściciela

- Liczbowa agregacja produkcyjna to średnia arytmetyczna. Nie ma edytora innych funkcji agregacji. Ocena jakościowa wykorzystuje katalog i regułę zgodności wszystkich punktów; metody rangowe muszą mieć jawnie zatwierdzony zbiór ocen zgodnych.
- Formularz eksportu zachowuje pomiary i metadane w układzie raportu laboratoryjnego, ale nie jest identyczną kopią graficzną oryginału. Nie odwzorowano podpisów, obrazów i scalonych obszarów 1:1.
- Daty rozpoczęcia i zakończenia oraz urządzenie są polami formularza i eksportu. Nie ma osobnego procesu podpisu zatwierdzającego ani katalogu przyrządów. Uwierzytelniony operator zatwierdza kompletną sesję; autoryzacja wynika z roli.
- Import jest kwarantanną historii. Nie rekonstruuje brakujących wersji tolerancji i nie promuje automatycznie danych historycznych do zatwierdzonych sesji ani SPC.
- Administrator tworzy i edytuje konta, role, aktywność oraz hasła. Zmiana konta unieważnia jego aktywne sesje. Nie ma samodzielnego odzyskiwania hasła przez e-mail.
- Tabele mają filtry, wyszukiwanie, sortowanie cyklu, dynamiczne kolumny i przewijanie. Nie ma dowolnego sortowania każdej kolumny ani edytora widoczności kolumn.
- Audit jest append-only przez API, bez zewnętrznego niezmiennego magazynu. SMTP nie potwierdza doręczenia do skrzynki. Awaria transmisji wymaga ręcznej obsługi.

Te elementy oraz odbiór na firmowej infrastrukturze oznaczają, że dostarczony kod nie jest jeszcze kompletnie odebraną aplikacją produkcyjną spełniającą każdy punkt specyfikacji.
