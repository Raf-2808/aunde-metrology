# AUNDE Metrologia

Zachowuj dane produkcyjne poza repozytorium. Nie zmieniaj oryginalnych plików ani portalu. Produkcja i nowe prywatne repozytorium wymagają zgody użytkownika.

Uruchamiaj pytest, testy PostgreSQL, build TypeScript i Playwright stosownie do zmiany. Nie deklaruj niewykonanych testów. Nie używaj znaku U+2014 w nowym tekście.

## 10A. Obowiązkowe standardy programowania, nazewnictwa i dokumentacji kodu

### 10A.1. Polskie nazwy funkcji

**Wymagam, aby wszystkie funkcje, metody, klasy i moduły tworzone na potrzeby logiki biznesowej aplikacji miały nazwy w języku polskim, o ile nie koliduje to ze standardami technicznymi lub wymaganiami wykorzystywanych frameworków.**

Przykłady:

- `pobierz_liste_przyrzadow()`
- `oblicz_date_nastepnego_sprawdzenia()`
- `sprawdz_waznosc_wzorcowania()`
- `zmien_status_przyrzadu()`
- `zapisz_historie_zmian()`
- `zarejestruj_odczyt_qr()`
- `generuj_kod_qr()`
- `eksportuj_przyrzady_do_excel()`
- `sprawdz_uprawnienia_uzytkownika()`
- `przywroc_usuniety_przyrzad()`

W kodzie stosuj polskie słowa bez znaków diakrytycznych w identyfikatorach.

Zachowaj odpowiednią konwencję:

- Python: `snake_case`.
- TypeScript / JavaScript: `camelCase`.
- Komponenty React: `PascalCase`.

Przykład TypeScript: `pobierzListePrzyrzadow()`.

**Wyjątki:** pozostaw oryginalne angielskie nazwy tam, gdzie wymagają tego Python, React, FastAPI, TypeScript, Docker, biblioteki zewnętrzne, standardowe interfejsy, dekoratory, funkcje systemowe lub mechanizmy frameworków.

Nie zmieniaj nazw standardowych metod i interfejsów, takich jak `__init__`, `useEffect`, `onClick`, `get`, `post`, ani nazw funkcji importowanych z bibliotek.

Nie tłumacz mechanicznie nazw, jeżeli pogorszyłoby to kompatybilność kodu lub utrudniło integrację.

### 10A.2. Obowiązkowe komentarze przed funkcjami

**Każda własna funkcja lub metoda powinna być poprzedzona komentarzem w języku polskim, który wyjaśnia jej przeznaczenie.**

Komentarz powinien wskazywać:

1. Cel funkcji i jej znaczenie w aplikacji.
2. Najważniejsze parametry wejściowe, jeśli występują.
3. Zwracany wynik.
4. Działania uboczne, np. zapis do bazy, zmianę statusu lub wygenerowanie zdarzenia.
5. Istotne ograniczenia, warunki lub wyjątki, jeśli występują.

Komentarze mają być zwięzłe, precyzyjne i zrozumiałe.

**Przykład w Pythonie:**

    # Oblicza termin następnego sprawdzenia przyrządu
    # na podstawie daty ostatniego sprawdzenia i interwału.
    #
    # Parametry:
    #   data_sprawdzenia: data ostatniego sprawdzenia
    #   interwal: liczba miesięcy pomiędzy sprawdzeniami
    #
    # Zwraca:
    #   datę następnego sprawdzenia
    #
    # Funkcja nie modyfikuje danych w bazie.

    def oblicz_date_nastepnego_sprawdzenia(
        data_sprawdzenia,
        interwal
    ):
        ...

**Przykład w TypeScript:**

    /**
     * Pobiera aktualny status wskazanego przyrządu
     * z backendu aplikacji.
     *
     * Parametry:
     *   identyfikator: unikalny identyfikator przyrządu
     *
     * Zwraca:
     *   dane przyrządu i jego aktualny status.
     *
     * Funkcja nie zmienia danych przyrządu.
     */
    async function pobierzStatusPrzyrzadu(
      identyfikator: string
    ) {
      // ...
    }

W Pythonie komentarz może znajdować się przed dekoratorami funkcji. Można dodatkowo zastosować docstring wewnątrz funkcji.

Zasada dotyczy backendu i frontendu, w tym funkcji pomocniczych, komponentów React, nazwanych funkcji obsługi zdarzeń i operacji bazodanowych.

Dla bardzo krótkich funkcji pomocniczych wystarczy jednozdaniowy komentarz.

Nie twórz sztucznych komentarzy do każdej trywialnej funkcji anonimowej przekazywanej jako callback. Takie funkcje powinny pozostawać czytelne, a bardziej złożoną logikę należy przenieść do nazwanych, udokumentowanych funkcji.

### 10A.3. Czytelność i organizacja kodu

Kod powinien być pisany w sposób ułatwiający jego późniejsze utrzymanie przez dział IT oraz rozwijanie z wykorzystaniem Codex.

W szczególności:

- Unikaj funkcji realizujących jednocześnie wiele niezależnych operacji.
- Rozdziel logikę biznesową, obsługę API, dostęp do bazy oraz prezentację danych.
- Stosuj opisowe nazwy zmiennych i funkcji.
- Nie stosuj niejasnych skrótów.
- Wyodrębniaj powtarzające się fragmenty kodu.
- Stosuj typowanie parametrów i wartości zwracanych.
- Dokumentuj skomplikowane algorytmy oraz reguły biznesowe.
- Unikaj nadmiernej liczby komentarzy opisujących oczywiste instrukcje.
- Zachowaj spójność nazewnictwa w całym projekcie.

Szczególnie zadbaj o przejrzystość funkcji odpowiedzialnych za:

- Obliczanie terminów sprawdzania.
- Określanie statusu metrologicznego.
- Zmianę stanu technicznego i przydziału.
- Zapisywanie historii zmian.
- Rejestrację odczytów QR.
- Kontrolę uprawnień.
- Generowanie plików Excel.
- Archiwizację i przywracanie przyrządów.

### 10A.4. Komunikaty błędów i diagnostyka

Komunikaty przeznaczone dla użytkownika powinny być w języku polskim.

Przykładowo:

- „Nie znaleziono przyrządu o podanym identyfikatorze”.
- „Nie można zmienić statusu przyrządu bez odpowiednich uprawnień”.
- „Wystąpił błąd podczas zapisywania danych”.
- „Termin sprawdzenia został przekroczony”.

Logi techniczne powinny zawierać:

- Datę i godzinę wystąpienia błędu.
- Nazwę modułu lub funkcji.
- Rodzaj wykonywanej operacji.
- Identyfikator zdarzenia umożliwiający diagnostykę.
- Szczegóły techniczne błędu, bez ujawniania haseł, tokenów i innych sekretów.

Komunikaty dla użytkownika nie mogą ujawniać wewnętrznej struktury bazy, zapytań SQL ani danych uwierzytelniających.

### 10A.5. Dokumentacja techniczna funkcji

Przygotuj dokument:

`docs/DOKUMENTACJA_FUNKCJI.md`

Dokument powinien zawierać zestawienie najważniejszych funkcji biznesowych w aplikacji.

Przykładowa struktura:

| Funkcja | Moduł | Opis działania |
|---|---|---|
| `oblicz_date_nastepnego_sprawdzenia()` | Terminy | Oblicza termin kolejnego sprawdzenia |
| `zmien_status_przyrzadu()` | Przyrządy | Aktualizuje status z kontrolą uprawnień |
| `zarejestruj_odczyt_qr()` | QR | Dodaje zdarzenie odczytu do historii |
| `eksportuj_przyrzady_do_excel()` | Eksport | Generuje XLSX z danymi i kodami QR |

Nazwy w dokumentacji muszą odpowiadać rzeczywiście zaimplementowanym funkcjom.

Dodatkowo opisz najważniejsze przepływy:

- Jak wyliczany jest status przyrządu.
- Co dzieje się po zmianie interwału sprawdzania.
- Jak rejestrowane jest otwarcie strony przez QR.
- Jak generowany jest eksport XLSX.
- W jaki sposób działa archiwizacja przyrządów.
- Jakie operacje wymagają uprawnień administratora.

### 10A.6. Wymagania dotyczące testów i odbioru kodu

Podczas przeglądu kodu sprawdzaj jego czytelność i zgodność ze standardem nazewnictwa.

Każda nowa funkcja biznesowa powinna:

- Mieć opisową polską nazwę, z wyjątkiem funkcji wymagających nazewnictwa technicznego.
- Posiadać komentarz bezpośrednio przed definicją lub przed zestawem dekoratorów.
- Mieć jasno określone parametry i typ zwracanego wyniku.
- Być możliwie niezależna od innych elementów aplikacji.
- Posiadać testy, jeśli realizuje istotną logikę biznesową.

Nie uznawaj zadania za zakończone, jeżeli kod działa, ale jest nieczytelny, nadmiernie skomplikowany lub nieudokumentowany.

### 10A.7. Obowiązkowa aktualizacja komentarzy i dokumentacji przy każdej zmianie kodu

**Wprowadzam bezwzględną zasadę: każda modyfikacja istniejącego kodu musi obejmować sprawdzenie, czy powiązane komentarze i dokumentacja nadal poprawnie opisują jego działanie.**

Jeżeli zmienia się logika funkcji, jej parametry, wynik, sposób obsługi błędów lub zależności, zaktualizuj odpowiedni komentarz.

Jeżeli zmienia się przebieg procesu biznesowego, zaktualizuj również odpowiedni dokument w katalogu `docs/`.

Dotyczy to w szczególności zmian w:

- Algorytmie wyznaczania dat sprawdzeń i wzorcowań.
- Logice wyznaczania statusu przyrządu.
- Sposobie modyfikowania rekordów.
- Mechanizmie generowania kodów QR.
- Rejestrowaniu i wyświetlaniu historii odczytów.
- Mechanizmach importu i eksportu danych.
- Uprawnieniach użytkowników i zabezpieczeniach.

**Nie pozostawiaj w repozytorium komentarzy, które opisują poprzednią wersję funkcji.**

Przed zakończeniem każdego zadania wykonaj kontrolę:

1. Czy nazwy nowych funkcji są zgodne z przyjętym standardem?
2. Czy nowe funkcje posiadają komentarze po polsku?
3. Czy komentarze do zmienionych funkcji nadal odpowiadają ich rzeczywistemu działaniu?
4. Czy dokumentacja techniczna została zaktualizowana, jeśli zmienił się opisany w niej proces?
5. Czy zmiana została objęta odpowiednimi testami?
6. Czy nie pojawiły się nieaktualne odwołania do usuniętych lub przemianowanych funkcji?

Informację o wykonaniu tej kontroli umieszczaj w podsumowaniu zadania lub opisie pull requestu.

### 10A.8. Obowiązkowe reguły w AGENTS.md

Umieść wszystkie wymagania niniejszego rozdziału w pliku `AGENTS.md`.

Codex ma traktować je jako stałe zasady projektowe obowiązujące również przy kolejnych zadaniach i nowych sesjach pracy nad repozytorium.

Nie ograniczaj ich stosowania do pierwszej wersji aplikacji.

**Cel nadrzędny: aplikacja musi być możliwa do diagnozowania, rozwijania i utrzymywania przez innego programistę lub dział IT, również bez udziału autora pierwotnego kodu.**

