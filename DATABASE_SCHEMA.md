# Schemat danych

| Tabela | Odpowiedzialność / relacje |
|---|---|
| users | Indywidualny login, Argon2, rola, active |
| login_sessions | Hash tokena, użytkownik, CSRF, czas wygaśnięcia, niezależne scopes |
| login_attempts | Limit prób logowania i ponownej autoryzacji |
| methods | Centralny katalog kodów i nazw metod |
| articles | Kod, nazwa, licznik zatwierdzonych cykli |
| article_configs | Nieusuwalna wersja artykułu, autor, data |
| characteristics | Charakterystyka konfiguracji, metoda, kolejność, specyfikacja JSON |
| orders | Lotto, artykuł, bela, ilość, zgłaszający, status, liczba sesji, badania dodatkowe |
| lab_sessions | Cykl i rewizja, zlecenie, konfiguracja, operator, data, ocena, uzasadnienie korekty |
| results | Sesja i charakterystyka, średnia i ocena źródłowa oraz symulowana |
| measurements | Osobny rekord każdego punktu, pozycja, oryginalna wartość i ocena |
| simulations | FK/PK measurement_id, wartość, korekta, algorytm, parametry i data |
| spc_configs | Charakterystyka konkretnej wersji, zatwierdzone granice, plan, autor |
| notification_rules | Charakterystyka, odbiorca, rodzaje alarmów, enabled |
| alerts | Unikalne zdarzenie sesja/konfiguracja/rodzaj |
| mail_outbox | Unikalny odbiorca alarmu, stan SMTP, data i błąd |
| dispositions | Historia wstrzymania i cofnięcia, użytkownik, data, uzasadnienie |
| audit | Autor, operacja, obiekt, treść zmiany, data |
| historical_rows | Surowe wiersze importu w kwarantannie, hash pliku i numer wiersza |

Pomiary nigdy nie są fizycznymi kolumnami przypisanymi do nazw badań. Tabela UI jest projekcją relacyjnych wyników. Specyfikacja JSON przechowuje zmienną konfigurację metody, nie pomiary. Wartości numeryczne zapisujemy jako kanoniczny tekst Decimal, aby zachować dokładną wartość wejścia i nie ograniczać typów jakościowych. Brak wyniku różni się od zera.

Unikalności: login, kod artykułu, norma, artykuł/wersja, konfiguracja/klucz, artykuł/lotto/bela, artykuł/cykl/rewizja, poprzednik korekty, sesja/charakterystyka, wynik/pozycja, alarm oraz odbiorca alarmu. Klucze obce i indeksy znajdują się w modelach i pierwszej migracji.

Nie udostępniamy API aktualizacji zatwierdzonych pomiarów. Dostęp administracyjny do bazy pozostaje odpowiedzialnością IT. Audit jest logicznie append-only na poziomie aplikacji; nie jest kryptograficznym rejestrem odpornym na ingerencję administratora PostgreSQL.
