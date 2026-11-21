# Test całego przebiegu na fikcyjnych danych

W lokalnej bazie przygotowano 4 artykuły `[DEMO]`, 31 zleceń, 21 zakończonych sesji i 2 karty SPC. Dane są zmyślone, łącznie z metodami, tolerancjami, granicami SPC i datami. Nie dotyczą rzeczywistych wyrobów AUNDE. Nie wysłano ani nie zakolejkowano wiadomości e-mail.

Stan początkowy kolejki: 9 oczekujących, 2 w trakcie, 19 zbadanych i 1 wstrzymane. Stan zmienia się podczas testowania.

## 1. Pierwsze kompletne badanie

W kolejce wybierz `DEMO-START-001`, artykuł **Aurora Silver H160**. Kliknij „Wykonaj badanie”.

| Charakterystyka | Pomiary do wpisania |
|---|---|
| Gramatura | 480; 482; 478 |
| Szerokość | 156,3; 156,5; 156,4 |
| Grubość | 3,00; 3,03; 2,97 |
| Wygląd powierzchni | ZGODNY |

Przy brakującym polu przycisk zapisu jest nieaktywny. Po skompletowaniu zapisz sesję. Partia przejdzie do „Zbadane”. Następnie można ją odszukać w wynikach rzeczywistych, symulowanych i Recover oraz wyeksportować do XLSX.

## 2. Czerwony pomiar i zgodna średnia

Użyj kolejnego lotto Aurory, np. `DEMO-START-002`. Dla grubości wpisz **2,70; 3,10; 3,15**, pozostałe dane jak powyżej.

Pierwszy pomiar będzie czerwony, ale średnia wyniesie ok. **2,98 mm**, czyli ocena charakterystyki pozostanie OK. Zapis wymaga potwierdzenia ostrzeżenia. W symulacjach 2,70 zostanie zastąpione wartością 2,82 i średnia symulowana będzie inna. Źródło pozostanie niezmienione.

Aby uzyskać średnią NOK, wpisz **3,30; 3,30; 3,30** i potwierdź ostrzeżenie. Historię takiego przykładu zawiera już `DEMO-HIST-A08`.

## 3. Dziesięć pomiarów i kilka sesji

Artykuł **Vega Graphite H150**:

- `DEMO-10-POMIAROW-001`: obowiązkowa adhezja w 10 punktach. Wpisz po **1,80** w każdym punkcie, grubość **4,50; 4,50; 4,50**, szerokość **147,5**, wygląd **ZGODNY**. Dziewięć punktów adhezji nie wystarczy do zapisu.
- `DEMO-DWIE-SESJE-001`: pierwsza z dwóch wymaganych sesji już istnieje. Zapis drugiej zakończy zlecenie. Poprzednia sesja pozostanie w historii.

## 4. Harmonogram co dziesiąte badanie

Artykuł **Terra Sand H180** ma 9 fikcyjnych zatwierdzonych cykli. Wybierz `DEMO-CYKL-10-001`, aby rozpocząć cykl 10. Formularz doda adhezję w 10 punktach.

Wpisz gramaturę **320**, grubość **1,79; 1,81; 1,80**, a w każdym z 10 punktów adhezji **1,20**. Po zakończeniu cyklu 10 następna zwykła sesja nie będzie wymagać tej adhezji. Jeżeli wcześniej wykonasz inne zlecenie tego artykułu, to właśnie ono otrzyma kolejny cykl. Harmonogram dotyczy artykułu, nie nazwy lotto.

## 5. Badanie dodatkowe, oceny jakościowe i wstrzymanie

Artykuł **Lyra Blue H165**:

- `DEMO-DODATKOWE-001`: zlecono dodatkową stabilność wymiarów. Wpisz siłę **125; 127; 123**, szerokość **161,7**, tarcie **4; 5; 4/5**, stabilność **-0,3; 0,1; 0,2**.
- `DEMO-JAKOSCIOWE-001`: zwykły zakres bez dodatkowej stabilności. Dla tarcia system nie oblicza średniej arytmetycznej.
- `DEMO-WSTRZYMANE-001`: gotowy przykład partii wstrzymanej z powodem w historii. Możesz cofnąć wstrzymanie z uzasadnieniem. Wyniki laboratoryjne pozostaną bez zmian.
- `DEMO-ZBADANE-001`: zgodny wynik, który można ręcznie wstrzymać i sprawdzić historię dyspozycji.

## 6. Wyniki, Recover i SPC

Moduły chronione wymagają własnego hasła konta. Wyszukaj lotto z prefiksem `DEMO-`. Wyniki nazywane w aplikacji rzeczywistymi są tutaj **fikcyjnymi danymi treningowymi**, wyraźnie oznaczonymi kodem i nazwą artykułu. Widok symulowany pokazuje pochodne transformacje tych samych fikcyjnych pomiarów.

W SPC przygotowano:

- **Grubość**, podgrupy po 3 pomiary, karta Xbar-R dla Aurory. Zawiera punkt poza granicą kontrolną i specyfikacją.
- **Gramatura**, pojedyncze obserwacje, karta I-MR dla Terry.

W Administracja > Powiadomienia znajdują się wyłączone reguły na adres `szkolenie@example.invalid`. Można obejrzeć ich konfigurację. Wysyłki nie włączano, a poczta nie jest potrzebna do testowania kolejki, pomiarów, symulacji, eksportów i kart SPC.

Przed zasileniem wykonano kopię lokalnej bazy w `.local/backups/`. Samych danych pomiarowych i kopii bazy nie publikuje się w GitHubie.
