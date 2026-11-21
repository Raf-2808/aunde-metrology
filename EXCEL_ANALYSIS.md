# Analiza skoroszytu referencyjnego

Analiza statyczna obejmuje arkusze `test`, `statistic`, ukrytą `matryca przejść`, `calc` i `recover`. Nie wykonywano VBA i nie modyfikowano źródła. Pełne wartości komórek, tolerancje, nazwy i źródła VBA pozostają wyłącznie w prywatnym pakiecie lokalnym `private/EXCEL_ANALYSIS_PRIVATE.md`, `private/excel_cells.json` i `private/vba/`.

## Przepływ

`test` zawiera formularz i aktualne tolerancje. `TransferDataOptimized` dopisuje 57 wartości do A:BE w `statistic`, od czwartego wiersza. Średnie i oceny pozostają formułami formularza, nie są zapisywane jako oddzielne dane historyczne. `recover` używa VLOOKUP po lotto i pobiera wybrane aktualne granice z `test`. `calc` tworzy serie średnich i zakresy dat dla wykresów.

`ClearCellsInTestSheet` czyści listę wejść formularza. Końcowy zakres J40:L40 nie jest kwalifikowany arkuszem. Pozostałe moduły nie zawierają dodatkowych procedur realizujących zapis. Kod VBA zastępują funkcje backendu, nie mechanizm uruchamiania makr.

## Mapowanie

| Pole / wiersz test | statistic według VBA | Element aplikacji i bazy |
|---|---|---|
| D7 | A | Numer lotto, orders.lot |
| J8 | B | Data badania, lab_sessions.test_date |
| D8 | C | Poziom produkcji, metadata.production_level |
| J7 | D | Bela, orders.roll |
| J9 / M7 | nieprzenoszone | Kod i nazwa artykułu |
| D9 | nieprzenoszone | WZ, metadata.delivery_note |
| 13 | E:G | Gramatura, 3 pomiary |
| 15 | H:J | Szerokość, 3 pomiary |
| 17 | K:M | Grubość, 3 pomiary |
| 19 / 20 | N:P / Q:S | Siła zrywająca w dwóch kierunkach |
| 22 / 23 | T:V / W:Y | Wydłużenie w dwóch kierunkach |
| 25 / 26 | Z:AB / AC:AE | Adhezja materiał/pianka |
| 28 / 29 | AF:AH / AI:AK | Adhezja pianka/siatka |
| 31 / 33 | AL:AN / AO:AQ | Oceny Cesconi, bez średniej arytmetycznej |
| 35 | AR:AT | Pilling, reguła jakościowa |
| 37 | AU | Taber, jeden wynik jakościowy |
| 39 / 40 | AV:AX / AY:BA | Palność w dwóch kierunkach |
| D41:D43 | BB:BD | Uwagi; historia zachowuje oddzielne kolumny |
| D45 | BE | Urządzenie w historii źródłowej i metadata.device nowych sesji |
| J47 / J49 | nieprzenoszone | Wykonujący / zatwierdzający; nowy system zapisuje operatora i audit |
| D47 / D49 | nieprzenoszone | Daty rozpoczęcia / zakończenia, metadata.started_on/ended_on |

Każda charakterystyka mapuje się na `characteristics` z odniesieniem do normy. J:L mapuje się na osobne `measurements`; M na `results.average`; N na `results.ok`. Normy E, granice F/G/H, jednostki I i oznaczenia P/Q są opisane dla każdego wiersza w prywatnej analizie. JSON komórek obejmuje także słowniki pomocnicze oraz wszystkie formuły.

## Rozbieżności

- `calc` zawiera 24 formuły z `#REF!`. Nie są importowane jako wyniki.
- `test` i `recover` różnią się normą gramatury i grubości oraz oceną Cesconi/Taber.
- W Taber część formuł porównuje wynik z pustą komórką. Metoda wymaga decyzji właściciela.
- Palność jest zapisywana kodami jakościowymi. Formuła kierunku poprzecznego odwołuje się do pustej komórki słownika.
- Recover wiersza 40 ma przesunięte indeksy kolumn względem VBA. Ukryta matryca nie obejmuje poprawnie wszystkich pól palności i uwag.
- VLOOKUP odtwarza tylko pierwszy rekord lotto. Aplikacja pokazuje osobne sesje i bele.
- Część granic Recover odczytuje z aktualnego test. Aplikacja utrwala niezmienną wersję konfiguracji.
- Znaki opisowe nie zawsze zgadzają się z operatorami formuły. Nie utożsamiamy automatycznie `>` i `>=`.
- Stare wymagania zależne od poziomu produkcji nie są równoznaczne z harmonogramem co N sesji. Częstotliwości trzeba zatwierdzić jawnie.

## Import historii

Historyczne wiersze są przechowywane oddzielnie, z SHA-256 pliku, numerem wiersza, każdą surową wartością i wykazem problemów. Import jest idempotentny. Nie zamienia NR ani pustych pól na liczby, nie przypisuje aktualnych tolerancji do dawnych danych, nie włącza historii do SPC i nie wysyła alarmów.
