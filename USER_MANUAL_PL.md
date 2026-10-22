# Instrukcja użytkownika

## Logowanie i role

Administrator tworzy indywidualne konta. Administrator i kierownik konfigurują metody, artykuły, SPC, odbiorców i dyspozycje partii. Laborant wykonuje badania, zgłaszający dodaje lotto, użytkownik odczytu ma dostęp do wyników rzeczywistych i SPC zgodnie z rolą.

W Administracja > Użytkownicy administrator może edytować rolę, aktywność i ustawić nowe hasło. Zapis unieważnia dotychczasowe sesje tego konta. Nie można samodzielnie odebrać własnemu kontu roli administratora ani go zablokować.

Przy wejściu do wyników rzeczywistych, symulowanych i SPC wpisz własne hasło. Każdy moduł jest odblokowany osobno na 15 minut. Przycisk „Potwierdź hasło” odświeża dostęp. Wylogowanie unieważnia sesję.

## Zlecenia i badanie

1. W „Zlecenia badań” rozwiń „Zgłoś nowe lotto”. Wybierz artykuł, podaj lotto i opcjonalnie belę oraz ilość. Kierownik może ustalić kilka sesji i dodatkowe charakterystyki.
2. Laborant wybiera „Wykonaj badanie”. Formularz otrzymuje właściwy cykl i wymagany zakres.
3. Uzupełnij datę, WZ, poziom produkcji, urządzenie, opcjonalne daty początku i końca oraz każde niebieskie pole. Białe pola opisują konfigurację. Liczba punktów wynika z metody, od jednego do dziesięciu.
4. Średnia jest liczona automatycznie. Czerwone pole oznacza przekroczenie pojedynczego pomiaru albo średniej. Pojedynczy wynik poza granicą nie zmienia automatycznie całej charakterystyki na NOK.
5. Potwierdź ostrzeżenia i zapisz. Niekompletnego badania nie można zatwierdzić. Kompletne NOK można i należy zarejestrować jako rzeczywisty wynik.
6. Jeśli pojawi się konflikt planu, odśwież go z kolejki. Inny operator mógł zatwierdzić kolejny cykl lub kierownik zmienił konfigurację.

Kafelki filtrują statusy. Partia jest zbadana po wykonaniu wszystkich wymaganych sesji. Nie jest to automatyczne zwolnienie do produkcji ani wysyłki.

## Wstrzymanie partii

Przy zbadanej partii wybierz „Wstrzymaj” i wpisz powód. Kierownik może cofnąć wstrzymanie z uzasadnieniem. Historia pokazuje autora i datę. Badania oraz OK/NOK pozostają niezmienione.

## Artykuły i normy

Najpierw dodaj normę do katalogu. Utwórz artykuł i charakterystyki. Wybierz normę z listy, jednostkę, typ wyniku, liczbę i etykiety punktów, granice z operatorami, liczbę miejsc dziesiętnych oraz harmonogram. Dla typu jakościowego zdefiniuj katalog i wyniki zgodne. Zapis tworzy nową wersję konfiguracji.

„Kopiuj do nowego” przenosi konfigurację jako propozycję. Wpisz nowy kod i nazwę. Historia starego artykułu nie jest kopiowana. „Przesuń wyżej” zmienia kolejność pól nowej wersji.

## Wyniki, Recover i korekty

Po potwierdzeniu hasła wyszukuj po lotto, artykule i datach. Każdy wiersz to osobna sesja. Nagłówki zawierają historyczną normę i granice. Kliknij lotto, aby otworzyć cały formularz. „Załaduj kolejne” pobiera dalsze sesje. Cykl można sortować.

Recover oferuje osobny wybór danych rzeczywistych i symulowanych. W przypadku wielu beli wybierz właściwy wiersz. Przy źródle rzeczywistym można także przeszukać historię Excela. Historia do weryfikacji nie jest zatwierdzoną sesją i nie posiada automatycznie odtworzonej oceny.

Kierownik w rzeczywistym formularzu może wybrać „Utwórz korektę”, podać powód i zapisać kompletny poprawiony formularz. Nowa rewizja zachowuje poprzednie wartości i numer cyklu. Nie służy to dopisywaniu pominiętych badań cyklicznych.

Eksport XLSX zawiera pojedyncze pomiary, średnie i tolerancje. Czerwone komórki nie mają dopisanego tekstu NOK. Symulacje mają oznaczenie SIMULATED DATA, także w eksporcie.

## Symulacje

System kopiuje zgodne liczby, a przekroczone punkty dwustronnej tolerancji przesuwa o 5% szerokości przedziału w stronę środka. Dla granicy jednostronnej potrzebna jest jawna korekta. Brak reguły pokazuje NO_RULE w formularzu. Dane symulowane nie wpływają na dyspozycję ani alarmy jakościowe.

## SPC i powiadomienia

W administracji kierownik zatwierdza plan próbkowania, liczność oraz CL/LCL/UCL średniej i rozstępu. Sam układ LH/M/RH nie stanowi dowodu poprawnej podgrupy. Zakres dat w wykresie nie przelicza zatwierdzonych granic.

W „Analiza SPC” wybierz konfigurację i daty. System pokazuje średnie oraz rozstępy (MR dla jednej obserwacji). Granice specyfikacji odróżniają się od kontrolnych. Eksportuj dane do XLSX lub zapisz wydruk wykresu jako PDF.

W administracji dodaj odbiorców, charakterystyki i rodzaje zdarzeń. Włącz lub wyłącz regułę przy odbiorcy. Włączenie rzeczywistej wysyłki wymaga także konfiguracji SMTP przez IT. Historia kolejki pokazuje przyjęcie do serwera lub problem. Dane symulowane nie uruchamiają tej kolejki.

## Import

W administracji wybierz plik XLSM/XLSX z arkuszem statistic. Import nie wykonuje makr i zapisuje surową historię do przeglądu. Powtórny import tego samego pliku nie dubluje wierszy. Puste i NR pozostają brakami. Nie importuj skoroszytu z nieznanego źródła do produkcji bez przeglądu danych.
