# Standardy pracy nad AUNDE LIMS

- Stos: React/TypeScript, FastAPI, SQLAlchemy, Alembic i PostgreSQL. SQLite wyłącznie dla testów jednostkowych i lokalnej pracy jednego operatora.
- Przed nietrywialną funkcją dodaj polski docstring lub komentarz. Stosuj polskie nazwy reguł domenowych; zachowuj nazwy standardowych API.
- Nie zmieniaj średniej na ocenę najgorszego pomiaru. Nie zaokrąglaj przed oceną.
- Backend wyznacza obowiązkowy zakres i wymaga wszystkich pomiarów. Nigdy nie zapisuj częściowej sesji jako zatwierdzonej.
- Zmiany konfiguracji tworzą nowe wersje. Korekty wyników zachowują poprzedni rekord, autora i uzasadnienie. Korekta nie przesuwa harmonogramu.
- Zapis sesji, symulacji, audytu i outbox wykonuj w jednej transakcji. Blokuj licznik artykułu i kontroluj przestarzały plan.
- Chronione tabele, eksport i Recover muszą sprawdzać rolę i aktualne potwierdzenie hasła osobno dla źródła.
- Nie umieszczaj prywatnego katalogu, skoroszytów, `.env`, historii ani haseł w Git. Nie używaj znaku U+2014 w nowym tekście.
- Do zmiany schematu dodawaj nową migrację Alembic. Nie edytuj zatwierdzonych rewizji. Przetestuj migracje na kopii bazy PostgreSQL i wykonaj backup przed wdrożeniem.
- Dla reguł biznesowych uruchom pytest. Dla formularzy uruchom Vitest, TypeScript i build. Zmiany współbieżności sprawdzaj na PostgreSQL, nie wyłącznie SQLite.
- Formatuj Python narzędziem Black, a React/TypeScript/CSS narzędziem Prettier. Nie kompresuj funkcji i formularzy do pojedynczych długich wierszy.
- Dane symulowane nie uruchamiają alarmów jakościowych ani nie zmieniają dyspozycji partii.
- SMTP w testach zastępuj atrapą. Wiadomości do prawdziwych odbiorców wymagają jawnego polecenia użytkownika.
- Każdy etap i ograniczenie weryfikacji opisz w VALIDATION.md. Nie deklaruj gotowości produkcyjnej bez odbioru na docelowej infrastrukturze.
