# Reguły biznesowe

1. Liczba punktów wynosi 1 do 10. Liczba unikalnych etykiet musi być identyczna z liczbą pomiarów.
2. Każdy wymagany punkt musi być wypełniony, także dla wyniku NOK. Puste pole nie jest zerem. Backend odrzuca nadmiarowe i pominięte charakterystyki.
3. Liczbowe charakterystyki używają średniej arytmetycznej. Pojedyncze przekroczenie wyświetla czerwone pole i ostrzeżenie. Ocena charakterystyki pochodzi ze średniej, nie z minimum zgodności pomiarów.
4. Porównujemy pełną dokładność wejścia. Średnia do prezentacji może być zaokrąglona; porównanie granic odbywa się przez sumę i liczność. Obsługiwane są operatory ostre i domknięte.
5. Wyniki jakościowe należą do zatwierdzonego katalogu. Wszystkie muszą należeć do zbioru ocen zgodnych. Nie obliczamy im średniej ani symulacyjnej korekty liczbowej.
6. Sesja jest NOK, gdy dowolna wymagana charakterystyka jest NOK. Ostrzeżenia wymagają świadomego potwierdzenia również przy średniej OK.
7. Harmonogram jest niezależny dla artykułu. Częstotliwości: każde, co N, dodatkowe zlecone przez kierownika. Plan nie zużywa cyklu. Zapis wyznacza zakres ponownie pod blokadą PostgreSQL.
8. Zlecenie zawiera wymaganą liczbę sesji i zlecone badania dodatkowe. ZBADANE oznacza wykonanie zakresu, nie formalne zwolnienie materiału.
9. Wstrzymanie zbadanej partii i cofnięcie wstrzymania wymagają roli kierownika/admina i powodu. Nigdy nie zmieniają wartości i statusów laboratoryjnych.
10. Dwustronna symulacja przesuwa przekroczony punkt o 5% szerokości tolerancji od granicy w stronę środka. Zgodne punkty pozostają bez zmian. Najpierw przekształcamy punkty, potem liczymy średnią.
11. Jednostronna symulacja wymaga dodatniego przesunięcia w jednostce metody. Brak reguły zachowuje źródło i zapisuje NO_RULE.
12. Symulacje nie zmieniają partii i nie wywołują alarmów. Widoki i eksporty mają oznaczenie SIMULATED DATA.
13. Zmiana konfiguracji tworzy nową wersję. Wyniki mają FK do starej konfiguracji. Korekty są kolejną rewizją tego samego cyklu, z autorem, datą, poprzednikiem i powodem.
14. Xbar-R wymaga n=2..10 i zatwierdzonej podgrupy. Dla n=1 karta I-MR. Zmienna liczność podgrupy jest odrzucana. Zakresy dat nie zmieniają zatwierdzonych granic.
15. Alarmy średniej, rozstępu, specyfikacji i serii po stronie CL są rozdzielone. Granica kontrolna nie jest automatycznie granicą zgodności wyrobu.
16. Alarm i outbox powstają tylko po zatwierdzeniu rzeczywistej sesji. Klucze unikalne blokują powtórne zlecenie tego samego zdarzenia.
17. Odczyt wyników, Recover i eksport wymagają właściwej roli i osobnego scope. Autoryzacja jednego źródła nie odblokowuje drugiego.
18. Historia Excela pozostaje oddzielną kwarantanną do weryfikacji. Braki i NR nie stają się zatwierdzonymi pomiarami.

Źródło współczynników i wzorów: [NIST Xbar-R](https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc321.htm) oraz [NIST I-MR](https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc322.htm). Tabela implementacji stosuje zaokrąglenia NIST do trzech miejsc, w tym D4=2.575 dla n=3 i D4=2.115 dla n=5. Propozycja granic pozostaje niezatwierdzona do decyzji kierownika.
