# Architektura

Przeglądarka komunikuje się z jednym origin przez Caddy. `/api` trafia do FastAPI, pozostałe ścieżki do statycznego React w Nginx. PostgreSQL nie publikuje portu hosta. Worker pobiera zatwierdzone zdarzenia z outbox. Backup używa pg_dump i trwałego katalogu.

Backend dzieli się na kontrakty Pydantic, reguły domenowe Decimal, modele SQLAlchemy, usługi transakcyjne, bezpieczeństwo, eksport, import i worker. UI wykonuje pomocniczą ocenę Number; ostateczna decyzja zawsze pochodzi z backendu.

Sesja HTTP-only zawiera losowy token; baza przechowuje jego SHA-256. Hasła haszowane Argon2. Mutacje wymagają CSRF, sprawdzany jest Origin. Potwierdzenie hasła nadaje 15-minutowe uprawnienie tylko do real, simulated albo spc. Role i scope kontrolowane przy każdym odczycie, także Recover i eksport.

Plan formularza nie rezerwuje numeru. Zapis blokuje artykuł i zlecenie, ponownie wyznacza cykl, wersję i charakterystyki. Przestarzały plan zwraca 409. Niekompletne dane zwracają 422 i nie zużywają cyklu. Wyniki, symulacje, audyt i outbox zatwierdzane są jednym commit.

Korekta to nowa rewizja tego samego cyklu, z odniesieniem do poprzedniej sesji i uzasadnieniem. Nie przesuwa harmonogramu. SPC wyklucza zastąpione rewizje, historia pozostaje dostępna w tabeli.

SMTP nie gwarantuje dokładnie jednokrotnego doręczenia. Unikalne klucze eliminują ponowne utworzenie alarmu i odbiorcy. Worker zapisuje SENDING przed transmisją; wynik niepewny pozostaje UNCERTAIN, bez automatycznej ponownej wysyłki. ACCEPTED_BY_SMTP oznacza przyjęcie przez serwer, nie potwierdzenie dostarczenia do skrzynki. Awaria po zapisie SENDING wymaga ręcznego sprawdzenia przez IT.

Tryb lokalny Windows używa SQLite i jest przeznaczony do pracy demonstracyjnej jednego operatora. Mechanizm row-level lock wymaga PostgreSQL na VM. Nie ma synchronizacji plików SQLite ani przechowywania produkcyjnych wyników w Excelu.
