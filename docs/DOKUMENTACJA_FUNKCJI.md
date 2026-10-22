# Funkcje i przepływy biznesowe

| Funkcja | Moduł | Rzeczywiste działanie |
|---|---|---|
| `sprawdz_konfiguracje()` | scripts/sprawdz_wdrozenie.py | Sprawdza konfigurację DEV/PROD bez wypisywania sekretów i bez uruchamiania usług |
| `sprawdz_docker()` | scripts/sprawdz_wdrozenie.py | Kontroluje Linux, silnik i składnię Compose bez migracji i zmian kontenerów |
| `normalizuj_wydzial()` | backend/reguly.py | Pomija rozpoznaną ulicę, zachowuje pozostałą nazwę |
| `oblicz_termin()` | backend/reguly.py | Dodaje dzień/miesiąc/rok z obsługą końca miesiąca |
| `sprawdz_daty()` | backend/reguly.py | Odrzuca brak/przyszły Ostatni dla aktywnego, daje n/a nieaktywnemu |
| `ocen_status()` | backend/reguly.py | Wyznacza ważność i dopuszczenie, bez modyfikacji ewidencji |
| `pobierz_rejestr()` | backend/ewidencja.py | Łączy bieżący przydział, właściwy harmonogram i statystyki QR |
| `filtruj_rejestr()` | backend/ewidencja.py | Stosuje filtry AND/OR, puste komórki i zakresy |
| `zmien_przyrzad()` | backend/ewidencja.py | Blokuje rekord, kontroluje wersję, waliduje i zapisuje zmiany/audyt |
| `dodaj_przyrzad()` | backend/ewidencja.py | Dodaje nieaktywny przyrząd B z wydziałem, harmonogramem i QR |
| `zarejestruj_czynnosc()` | backend/api.py | Dodaje rzeczywisty wynik sprawdzenia/wzorcowania i aktualizuje harmonogram |
| `zmien_token()` | backend/api.py | Unieważnia dotychczasowy QR i tworzy nowy, audytuje operację |
| `zarejestruj_odczyt()` | backend/publiczne.py | Tworzy spójną migawkę i zdarzenie pod blokadą, COMMIT przed sukcesem |
| `przygotuj_karte()` | database/publiczne.sql | Zwraca jawnie dozwolone pola i blokuje rekord przed zmianą w transakcji |
| `zapisz_odczyt()` | database/publiczne.sql | Zapisuje publiczny odczyt z deduplikacją ID i listą dozwolonych kluczy |
| `historia_karty()` | database/publiczne.sql | Zwraca paginowaną historię statusów, niczego nie zapisuje |
| `zbuduj_excel()` | backend/eksport.py | Tworzy XLSX z tekstem, datami, obrazami QR i aktywnymi linkami |
| `importuj_excel()` | backend/obsluga.py | Próbnie waliduje lub atomowo importuje uzgodniony plik do pustej ewidencji |
| `obsluz_powiadomienia()` | backend/obsluga.py | Kolejkuje nowe przekroczenia i wysyła przez SMTP tylko po włączeniu |
| `czy_wymaga_alertu()` | backend/obsluga.py | Rozpoznaje przekroczony wymagany termin także przy innej przyczynie blokady |
| `zalogowany()` | backend/api.py | Kontroluje ważność sesji, aktywność konta i CSRF |
| `pobierz_konta()` | backend/api.py | Udostępnia Administratorowi role i aktywność bez skrótów haseł |
| `zmien_konto()` | backend/api.py | Zmienia rolę/aktywność/hasło, unieważnia sesje i chroni ostatniego Administratora |
| `Konta()` | frontend/src/Konta.tsx | Obsługuje dodawanie i edycję kont w panelu |
| `zapisz()` | frontend/src/main.tsx | Zapisuje pojedynczą komórkę z wersją, pokazuje błąd konfliktu |
| `otworzFiltr()` | frontend/src/main.tsx | Pobiera kontekstowe wartości ze wszystkich pasujących rekordów |
| `KartaPubliczna()` | frontend/src/main.tsx | Pokazuje kartę mobilną i automatycznie rejestruje otwarcie |

## Status i terminy

Data bazowa, interwał i jednostka wyznaczają termin. Ręczne nadpisanie Administratora ma pierwszeństwo i wymaga uzasadnienia. Status jest oceniany na dzień Europe/Warsaw, a nie tylko przy zapisie. Po przekroczeniu terminu dopuszczenie jest fałszywe, nawet gdy Status ewidencyjny to Aktywna i stan techniczny jest Sprawny. Pole przyrzady.odblokowany przechowuje ręczną decyzję. Wynik to ręczne Odblokowany AND brak przekroczenia wymaganego terminu AND stan inny niż Niesprawny. Sprawny usuwa blokadę niesprawności bez znoszenia innych przyczyn. Aktywność służy tylko inicjalizacji przy migracji/importowaniu; stan zwrotu, brak wyniku i wynik negatywny nie są automatycznymi blokadami. Nowy nieaktywny rekord ma ręczne Zablokowany. Ręczna zmiana jest wersjonowana i audytowana; backend odrzuca próbę odblokowania przy trwającej przyczynie automatycznej. Te same reguły obowiązują rejestr, eksport i QR.

Zmiana interwału nie zmienia daty Ostatni. Wyliczony termin jest natychmiast inny w tabeli i karcie. Edycja daty usuwa założenie o wyniku, a zarejestrowanie rzeczywistej czynności zapisuje datę, wynik i autora w odpowiednim procesie. Skan QR nie zmienia żadnego z tych pól.

## Otwarcie QR

Frontend widocznej karty wysyła UUID otwarcia. Backend publiczny odczytuje ograniczony zakres pod blokadą, oblicza status dla tego samego zestawu danych i przekazuje migawkę funkcji zapisu. Czas oceny statusu i czas zdarzenia pochodzą z tego samego transaction_timestamp PostgreSQL, także przy przejściu przez północ. Dopiero COMMIT daje poprawną odpowiedź. Powtórzenie UUID zwraca wcześniejszy zapis. Zasoby i historia niczego nie rejestrują. Ostatni odczyt i liczba w panelu oraz karcie publicznej są agregowane z tej samej tabeli historii.

## Eksport

Administrator wybiera wszystkie rekordy albo bieżące filtry. Backend sprawdza uprawnienia, pobiera dane i aktualne tokeny, tworzy XLSX lokalnie. W kolumnach A-K zachowuje układ źródła. Kolumna S „Adres karty QR” zawiera tekst URL z hiperłączem. Ostatnia kolumna T „Kod QR” zawiera wyłącznie obraz, a komórka pod obrazem pozostaje pusta. Eksport nie rotuje tokenów. Tekstowe dane zaczynające się od znaku równości są zapisywane jako tekst, bez uruchamiania formuł.

## Archiwizacja i role

Administrator potwierdza kosz. Zapis `usunieto_at`, podniesienie wersji i audyt należą do tej samej transakcji; historia pozostaje. Przywrócenie wymaga zgodnej wersji i ponownej oceny wymaganych dat. Editor nie archiwizuje, nie rotuje QR, nie nadpisuje terminu i nie czyta R&R. Viewer nie zmienia danych. Każda mutacja administracyjna poza logowaniem wymaga ważnej sesji i CSRF.

## Kontrola dokumentacji

Przy każdej zmianie funkcji sprawdź jej nazwę, komentarz przed definicją, typy, testy i ten dokument. Zmiana logiki terminu, publikacji danych lub uprawnień wymaga również aktualizacji MODEL_DANYCH.md, instrukcji obsługi i testów. Nie zmieniaj wstecznie opisu wyników testów, których nie wykonano.

Powiadomienia są ponownie oceniane pod blokadą konkretnego przyrządu bezpośrednio przed wysyłką, a dane wiadomości odświeżane. Wynik negatywny nie ukrywa potrzeby alertu przekroczonego terminu. Połączenie SMTP używa STARTTLS z kontekstem weryfikującym certyfikat. Reguły scalenia importu pochodzą z jawnego lokalnego JSON poza repozytorium, bez numerów produkcyjnych w kodzie.
