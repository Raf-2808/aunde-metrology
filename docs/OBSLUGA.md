# Obsługa ewidencji i kodów QR

## Rejestr i uprawnienia

Zaloguj się lokalnym kontem. Viewer przegląda i filtruje, Editor edytuje pola i rejestruje rzeczywiste czynności, Administrator dodatkowo zarządza kontami, eksportuje, archiwizuje, przywraca, rotuje QR i nadpisuje termin. R&R nie jest dostępne dla Viewer/Editor ani dla użytkownika publicznego. Sesja trwa do ośmiu godzin; po wylogowaniu token jest unieważniony po stronie serwera.

Przycisk Zarządzaj kontami pozwala Administratorowi dodawać konta, zmieniać role, dezaktywować/aktywować i ustawiać nowe hasło. Każda zmiana unieważnia sesje danego konta. Nie można wyłączyć ani pozbawić roli ostatniego aktywnego Administratora. Hasła nie są wyświetlane ani odczytywane z serwera.

Kliknij nagłówek kolumny. Lista obejmuje wartości przy wszystkich pozostałych filtrach, a nie tylko bieżącą stronę. Użyj wyszukiwania, checkboxów, zaznaczania wszystkich, pustych lub zakresu dat/liczb. Sortowanie wybierz w tym samym panelu. Przycisk Wyczyść filtry przywraca pełny widok. Liczba rekordów pokazuje wynik filtrów.

Kliknij edytowalną komórkę. Typ i Wydział mają podpowiedzi, stałe pola słownikowe listy, daty kalendarz. Enter lub opuszczenie pola zapisuje. Escape anuluje. Jeśli ktoś zmienił rekord wcześniej, zobaczysz konflikt; odśwież i oceń cudzą zmianę. Nie ponawiaj zapisu bez zapoznania się z aktualną wartością.

Wydział zapisuje się bez dopisku ulicy. Cutter Wersalska i Cutter Senatorska to Cutter. Wybierz nazwę z listy zamiast dopisywać lokalizację. Grupa ma początkowo B dla wszystkich. Późniejsza zmiana na A/C wymaga uzasadnienia i przełącza właściwy proces nadzoru, nie zmieniając wcześniejszych zdarzeń.

## Daty i czynności

Ostatni jest datą ostatniej właściwej czynności, nie ostatniego odczytu QR. Interwał i jednostka określają Następny. Przekroczony termin blokuje użytkowanie również przy Status Aktywna. Sprawny stan techniczny nie znosi tej blokady.

Aktywny przyrząd musi mieć poprawną, nieprzyszłą datę Ostatni. Brak lub przyszły Ostatni jest dopuszczalny tylko dla Nieaktywna z automatycznym komentarzem n/a. Dla nieaktywnego nie oznacza to dopuszczenia do użycia. Przyszła data Następny jest normalna.

Po wykonaniu rzeczywistego sprawdzenia lub wzorcowania użyj Zapisz czynność: wpisz rzeczywistą datę i wynik. Dla A podaj także numer świadectwa lub raportu wewnętrznego. Funkcja zapisze historię i przeliczy termin. Zwykła korekta daty nie jest pozytywnym wynikiem. Dane zaimportowane bez znanej sprawności i wyniku nie uzyskują automatycznego dopuszczenia.

Administrator może zmienić Następny, podając uzasadnienie. Wyczyszczenie nadpisania z uzasadnieniem przywraca termin z interwału. Przy aktywnym nadpisaniu najpierw wycofaj je, zanim zmienisz interwał lub datę bazową.

## Archiwum

Ikona kosza otwiera potwierdzenie. Po zatwierdzeniu przyrząd znika z aktywnego rejestru, lecz pozostaje w archiwum wraz z historią. Administrator może włączyć Archiwum i użyć Przywróć. Powrót do rejestru nie jest potwierdzeniem aktualnej ważności lub sprawności. Publiczna karta zarchiwizowanego przyrządu jest niedostępna.

## Publiczna karta QR

Kod zawiera tylko URL z losowym tokenem. Wystarczy zwykła przeglądarka Android/iOS. Karta pokazuje bieżące dane przyrządu, wydział bez ulicy, grupę i dopuszczenie. R&R nie jest zwracane przez publiczny backend. Nie są wymagane konto, numer pracownika, instalacja aplikacji ani potwierdzenie OK/NOK.

Po skutecznym otwarciu widocznej karty powstaje zdarzenie z czasem i migawką statusu. Powtórne otwarcie lub odświeżenie tworzy nowe zdarzenie; ponowienie nieudanego żądania używa tego samego identyfikatora. Bieżący odczyt jest pokazany nad historią; interfejs historii publicznej pomija wpisy niepoprzedzające tego odczytu. Paginacja nie tworzy nowych zdarzeń. Data i czas są prezentowane w Europe/Warsaw.

Odczyt QR nie zmienia przydziału, stanu, interwału, wyników ani dat metrologicznych. Nie jest dowodem fizycznego sprawdzenia przyrządu przez pracownika. Nie udostępniaj linku szerzej, niż jest to potrzebne. Administrator może unieważnić stary QR przyciskiem Nowy QR. Dotychczasowe etykiety przestaną wtedy działać i wymagają wymiany.

## Excel i powiadomienia

Administrator wybiera Eksport wyników albo Eksport całości. Plik XLSX zawiera R&R, obrazy QR i aktywne linki. QR nie wymaga zewnętrznego serwisu generowania. Eksport nie zmienia tokenów. Po zmianie docelowej domeny IT musi ocenić trwałość już wydrukowanych kodów.

Blokady terminów są wyliczane niezależnie od poczty. Po zatwierdzeniu i włączeniu przez IT moduł wysyła alerty do jakosc@aunde.pl. Awaria SMTP nie odblokowuje przyrządu. Domyślnie wysyłka pozostaje wyłączona do próby i ustalenia częstotliwości.
