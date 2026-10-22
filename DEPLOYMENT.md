# Wdrożenie na firmowej VM Linux

## Wymagania

Docker Engine z Compose v2, VM z dostępem do rejestrów pakietów przy budowaniu, trwały dysk, firmowy DNS, porty 80/443 oraz wewnętrzny SMTP z STARTTLS. Na tym komputerze nie był dostępny Docker, więc odbiór Compose wymaga uruchomienia na VM lub runnerze CI.

## Pierwsze uruchomienie

```sh
cp .env.example .env
chmod 600 .env
# Ustaw wartości w .env przed kolejnym poleceniem.
docker compose config --quiet
docker compose up -d --build
docker compose ps
docker compose exec backend python -m app.cli create-admin --login admin
```

Hasło PostgreSQL generuj w menedżerze haseł. W `DATABASE_URL` hasła muszą być poprawnie zakodowane dla URL, dlatego w tym wariancie Compose użyj co najmniej 32 losowych znaków alfanumerycznych. Sekrety nie należą do repozytorium. Dla środowiska z firmowym vault wstrzykuj je przed uruchomieniem Compose. Nie publikuj portu PostgreSQL ani backendu.

`PUBLIC_URL` musi zawierać dokładny protokół, host i ewentualny port używany przez przeglądarkę. `SITE_ADDRESS` określa nazwę w Caddy, a `ALLOWED_HOSTS` dopuszczalne hosty bez protokołu. Cookie Secure pozostaw true dla HTTPS.

Caddy używa `tls internal`. IT musi rozprowadzić zaufanie do lokalnego CA Caddy lub zastąpić tę sekcję firmowym certyfikatem i kluczem montowanymi tylko do odczytu. Przy firmowym reverse proxy dopasuj trasowanie `/api/*`, Origin i HTTPS; nie pozostawiaj niezaufanego HTTP dla produkcji.

Utwórz użytkowników, katalog norm i artykuły. Prywatny katalog referencyjny można wczytać poleceniem `python -m app.cli load-catalog --file /sciezka/katalog.json --login admin`, lecz dopiero po zatwierdzeniu norm i harmonogramu przez właściciela metody. Nie zawiera on automatycznie sześciu niejednoznacznych metod jakościowych.

## SMTP

Ustaw SMTP_HOST, SMTP_PORT, SMTP_FROM oraz opcjonalne SMTP_USER/SMTP_PASSWORD. Po zatwierdzeniu odbiorców i testu na skrzynce technicznej ustaw SMTP_ENABLED=true i odtwórz backend/worker. Samo dodanie reguły nie włącza SMTP. Worker wymaga STARTTLS z poprawnym certyfikatem. Nie obniżaj weryfikacji certyfikatu.

Opcja SMTP_ATTACH_CHART=true dodaje załącznik graficzny SVG z trendami średniej i rozstępu. Wiadomość zawsze zawiera dane alarmu i link do karty. SVG otwiera się jako załącznik; klienci pocztowi mogą blokować jego podgląd w treści.

Stany: PENDING, SENDING, ACCEPTED_BY_SMTP, UNCERTAIN. Dwa ostatnie nie są potwierdzeniem dostarczenia do skrzynki odbiorcy. W przypadku SENDING po awarii lub UNCERTAIN sprawdź Message-ID w logach SMTP. Nie ustawiaj PENDING ponownie bez sprawdzenia, czy serwer już przyjął wiadomość. Zdarzenia nie są automatycznie ponawiane przy niepewnym wyniku, co zapobiega duplikatom kosztem ręcznej obsługi awarii.

## Backup

Kontener backup zapisuje archiwum pg_dump -Fc co 24 godziny i usuwa kopie starsze niż 30 dni. Podmontuj `backups/` na dysk z ograniczonym dostępem. Co najmniej jedna kopia powinna trafiać poza VM do firmowego systemu backupu. Skrypt lokalny nie realizuje szyfrowania poza mechanizmem dysku i nie zastępuje polityki kopii offsite.

Kopia na żądanie:

```sh
docker compose exec backup sh -c 'pg_dump -Fc -f /backups/manual.dump'
docker compose exec backup pg_restore --list /backups/manual.dump
```

## Restore

Przetestuj na odrębnej VM. Wstrzymaj zapis i worker. Zachowaj uszkodzoną bazę i nowsze kopie przed odtworzeniem.

```sh
docker compose stop backend worker
docker compose exec backup sh -c 'pg_restore --clean --if-exists --no-owner -d "$PGDATABASE" /backups/manual.dump'
docker compose run --rm migrate
docker compose up -d backend worker
```

Odtwarzanie nadpisuje bieżące dane, dlatego wykonuje je uprawniony administrator po zatwierdzeniu docelowej bazy. Po restore zweryfikuj liczbę sesji, ostatni cykl, historię i outbox przed wznowieniem SMTP.

## Aktualizacja

1. Wykonaj backup i sprawdź listę archiwum.
2. Pobierz zatwierdzony commit. Nie używaj automatycznego merge do głównej gałęzi.
3. Przeczytaj nowe migracje i przetestuj je na odtworzonej kopii PostgreSQL.
4. Zatrzymaj backend i worker, wykonaj `docker compose build`, `docker compose run --rm migrate`, a następnie `docker compose up -d`.
5. Sprawdź healthcheck, logowanie, dodatkowe hasło, zapis kompletnej sesji i eksport.
6. W razie niezgodnej migracji przywróć bazę z kopii wraz z poprzednią wersją aplikacji. Sam rollback obrazu nie cofa schematu.

## Monitorowanie

Monitoruj `docker compose ps`, logi backendu/worker/proxy, wiek ostatniej kopii, miejsce na dysku i liczbę PENDING/SENDING/UNCERTAIN w outbox. Healthcheck worker sprawdza dostęp do bazy, nie potwierdza działania SMTP. Kontener backup sygnalizuje awarię logiem; alarm o braku świeżej kopii musi skonfigurować IT.
