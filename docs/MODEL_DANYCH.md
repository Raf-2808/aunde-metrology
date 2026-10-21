# Model danych i mapowanie źródła

`backend/modele.py` definiuje encje, a zamrożone migracje Alembic tworzą strukturę i indeksy PostgreSQL. UUID jest trwałym kluczem przyrządu. Numer jest tekstem i ma ograniczenie unikalności po uzgodnionym połączeniu duplikatu. Lp jest licznikiem widoku, nie kluczem importu.

| Źródłowe pole | Przechowywanie i reguła |
|---|---|
| Lp | `wiersze_importu.surowe`, licznik UI wyliczany |
| Numer | `przyrzady.numer`, bez utraty zer i znaków |
| Typ | `typy_przyrzadow`, FK w przyrządzie |
| Stan | `przyrzady.stan`, Na stanie/Zwrócona |
| Status | `przyrzady.status`, Aktywna/Nieaktywna; odrębny od metrologii |
| Wydział / Przydział | `wydzialy` i historia `przydzialy`; znana ulica usunięta |
| Grupa | `przyrzady.klasa`, A/B/C, początkowo B dla wszystkich |
| R&R | `dane_rr`, tylko panel Administratora i jego eksport |
| Ostatni | `harmonogramy.ostatni`, DATE, źródłowa podstawa bez fikcyjnego wyniku |
| Interwał | `harmonogramy.interwal`, dodatnia liczba, jednostka osobno |
| Następny | źródłowy `termin_zrodlowy`; bieżący termin obliczany lub jawnie nadpisany |

Pozostałe encje: `sprawdzenia`, `wzorcowania`, `linki_qr`, `odczyty_qr`, `historia_statusow`, `audyt`, `uzytkownicy`, `sesje`, `importy`, `wiersze_importu`, `powiadomienia_email`. Słowniki o stałych wartościach A/B/C oraz stanów i statusów są typowanymi polami z walidacją i ograniczeniami zamiast dodatkowych pustych tabel słownikowych. Dynamiczne nazwy typów i wydziałów są osobnymi tabelami. To doprecyzowanie modelu logicznego ETAPU 0.

Harmonogram przechowuje bieżącą datę bazową oraz opcjonalne nadpisanie z uzasadnieniem. Zmiany są audytowane; rzeczywiste czynności dodają oddzielne, nieusuwane wpisy sprawdzeń lub wzorcowań. Import nie dopisuje nieznanych wyników i nie udaje historycznych czynności. Zmiana klasy tworzy/wybiera harmonogram właściwego procesu, nie kopiuje daty automatycznie pomiędzy procesami. C zachowuje historię, a bieżący status opisuje brak wymogu okresowego. Nadal obowiązuje reguła użytkownika o poprawnych datach przy aktywacji, dopóki nie zatwierdzi wyjątku dla aktywnej C.

Przywrócenie i archiwizacja zachowują relacje. Częściowe indeksy zapewniają jeden otwarty przydział i jeden aktywny QR. Rotacja QR jest osobną operacją z kontrolą wersji. Archiwalna karta jest niedostępna, po przywróceniu działa bieżący aktywny token. Soft delete nie usuwa historii.

Publiczna rola DB nie ma SELECT do tabel. Może wykonać tylko trzy funkcje SECURITY DEFINER ze stałym search_path: przygotowanie karty pod blokadą rekordu, zapis odczytu i pobranie historii. Wszystkie trzy mają odebrane EXECUTE od PUBLIC. Funkcja zapisu dodatkowo odrzuca klucze spoza publicznej listy, więc R&R nie trafia do migawki także przy wadliwym wywołaniu backendu. Panel administracyjny blokuje ten sam rekord przy edycji, co utrzymuje spójność migawki QR.

Identyfikator odczytu jest UUID tworzonym na otwarcie karty. Ponowienie żądania używa tego samego ID. Odświeżenie i powrót z pamięci nawigacji tworzą nowe ID. Pobieranie historii, zasobów oraz podglądy HEAD/prefetch nie są zdarzeniami. Automatyczna przeglądarka nadal może naśladować człowieka; odczyt nie potwierdza fizycznej czynności ani osoby.

Czas statusu i zapisu zdarzenia jest jednym czasem transakcji PostgreSQL. Funkcje migrują się z zamrożonych plików SQL przypisanych do wersji Alembic. Pole `database/publiczne.sql` jest aktualnym czytelnym kontraktem funkcji, a migracje nie pobierają go dynamicznie zamiast historycznej wersji.

Filtry i paginacja działają na serwerze. Na obecnej skali około 2134 przyrządów backend wykonuje złączenie i agregat QR, następnie filtruje wyliczane pola w pamięci serwera. Zwraca tylko stronę wyników. Nie jest to rozwiązanie do milionów rekordów: przed znacznym wzrostem danych należy przenieść obliczane filtry do indeksowanego zapytania PostgreSQL i zmierzyć plan zapytania. Podpowiedzi nie są ograniczone do strony.

Wzorce terminów: miesiące i lata kalendarzowe z ograniczeniem dnia do końca miesiąca, dni jako dni kalendarzowe. Termin ważny do końca dnia w Warszawie; ostrzeżenie 30 dni. Są to jawne domyślne reguły implementacji do potwierdzenia biznesowego. Ręczna zmiana terminu wymaga Administratora i uzasadnienia. Zmiana interwału z aktywnym nadpisaniem jest odrzucana do jego wycofania. Rejestracja nowej rzeczywistej czynności zamyka nadpisanie, co widać w audycie.

Brak ulicy w widokach nie usuwa oryginalnych źródeł: surowe wiersze importu zachowują oryginalną nazwę wydziału i Grupę. Dokumenty źródłowe i te dane nie należą do GitHub ani publicznego API.
