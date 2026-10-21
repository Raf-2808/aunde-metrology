import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { createRoot } from "react-dom/client";
import { createPortal } from "react-dom";
import {
  ColumnDef,
  flexRender,
  getCoreRowModel,
  useReactTable,
} from "@tanstack/react-table";
import {
  wywolajApi,
  ustawCsrf,
  tokenCsrf,
  pokazWartosc,
  type Sesja,
  type Filtry,
  type Filtr,
  type Rekord,
  type Wartosc,
} from "./api";
import "./styl.css";
import { Konta } from "./Konta";

const KOLUMNY: [string, string][] = [
  ["numer", "Numer"],
  ["typ", "Typ"],
  ["stan", "Stan"],
  ["status", "Status"],
  ["wydzial", "Wydział"],
  ["klasa", "Grupa"],
  ["rr", "R&R"],
  ["ostatni", "Ostatni"],
  ["interwal", "Interwał"],
  ["nastepny", "Następny"],
  ["jednostka", "Jednostka"],
  ["stan_techniczny", "Stan techniczny"],
  ["metrologiczny", "Status metrologiczny"],
  ["dopuszczenie", "Dopuszczenie"],
  ["komentarz_dat", "Komentarz"],
  ["ostatni_qr", "Ostatni odczyt QR"],
  ["liczba_qr", "Odczyty QR"],
];
const SLOWNIKI: Record<string, string[]> = {
  stan: ["Na stanie", "Zwrócona"],
  status: ["Aktywna", "Nieaktywna"],
  klasa: ["A", "B", "C"],
  rr: ["---", "Tak"],
  jednostka: ["dzien", "miesiac", "rok"],
  stan_techniczny: ["Nieustalony", "Sprawny", "Niesprawny"],
};

/** Wyświetla oficjalne logo AUNDE zapisane lokalnie oraz nazwę systemu i konto użytkownika. */
function Naglowek({
  sesja,
  wyloguj,
}: {
  sesja?: Sesja;
  wyloguj?: () => void;
}): React.ReactElement {
  return (
    <header className="naglowek">
      <img
        className="marka"
        src="/logo-aunde.png"
        alt="AUNDE"
        width="150"
        height="45"
      />
      <div className="nazwa">
        Metrologia<span>Zarządzanie przyrządami pomiarowymi</span>
      </div>
      {sesja && (
        <div className="konto">
          <span>
            {sesja.login}
            <small>{sesja.rola}</small>
          </span>
          <button onClick={wyloguj}>Wyloguj</button>
        </div>
      )}
    </header>
  );
}

/** Loguje użytkownika lokalnego i przekazuje sesję; błąd pozostaje przy formularzu. */
function Logowanie({
  gotowe,
}: {
  gotowe: (s: Sesja) => void;
}): React.ReactElement {
  const [blad, ustawBlad] = useState("");
  const [zapis, ustawZapis] = useState(false);
  /** Odczytuje formularz, ustanawia sesję i czyści stan oczekiwania także po błędzie. */
  async function zaloguj(e: React.FormEvent<HTMLFormElement>): Promise<void> {
    e.preventDefault();
    ustawZapis(true);
    ustawBlad("");
    const dane = new FormData(e.currentTarget);
    try {
      gotowe(
        await wywolajApi<Sesja>("/api/logowanie", "POST", {
          login: dane.get("login"),
          haslo: dane.get("haslo"),
        }),
      );
    } catch (b) {
      ustawBlad((b as Error).message);
    } finally {
      ustawZapis(false);
    }
  }
  return (
    <>
      <Naglowek />
      <main className="logowanie">
        <div className="opis">
          <span className="nadtytul">NADZÓR METROLOGICZNY</span>
          <h1>
            Każdy przyrząd.
            <br />
            Aktualny status.
          </h1>
          <p>
            Ewidencja, terminy sprawdzeń i historia odczytów w jednym miejscu.
          </p>
          <div className="pasek" />
        </div>
        <form onSubmit={zaloguj} className="karta">
          <h2>Zaloguj się</h2>
          <p>Użyj lokalnego konta aplikacji.</p>
          <label>
            Login
            <input name="login" autoComplete="username" required autoFocus />
          </label>
          <label>
            Hasło
            <input
              name="haslo"
              type="password"
              autoComplete="current-password"
              required
            />
          </label>
          {blad && (
            <p role="alert" className="blad">
              {blad}
            </p>
          )}
          <button className="glowny" disabled={zapis}>
            {zapis ? "Logowanie…" : "Przejdź do ewidencji"}
          </button>
        </form>
      </main>
    </>
  );
}

/** Pozwala wybrać wiele wartości, puste i zakres, zachowując dostępność klawiatury. */
function FiltrKolumny({
  pole,
  filtr,
  wartosci,
  zatwierdz,
  sortuj,
  zamknij,
}: {
  pole: string;
  filtr: Filtr;
  wartosci: { wartosc: Wartosc; liczba: number }[];
  zatwierdz: (f: Filtr | null) => void;
  sortuj: (m: boolean) => void;
  zamknij: () => void;
}): React.ReactElement {
  const [szukaj, ustawSzukaj] = useState("");
  const [wybrane, ustawWybrane] = useState<Wartosc[]>(
    filtr.wartosci ?? wartosci.map((w) => w.wartosc),
  );
  const [od, ustawOd] = useState(filtr.od || "");
  const [doDaty, ustawDo] = useState(filtr.do || "");
  const widoczne = wartosci.filter((w) =>
    pokazWartosc(w.wartosc)
      .toLocaleLowerCase("pl")
      .includes(szukaj.toLocaleLowerCase("pl")),
  );
  const zakres = ["ostatni", "nastepny", "interwal", "liczba_qr"].includes(
    pole,
  );
  return createPortal(
    <div className="filtr" role="dialog" aria-label="Filtr kolumny">
      <div className="rzad">
        <strong>Filtr kolumny</strong>
        <button aria-label="Zamknij filtr" onClick={zamknij}>
          ×
        </button>
      </div>
      <div className="rzad">
        <button onClick={() => sortuj(false)}>Rosnąco ↑</button>
        <button onClick={() => sortuj(true)}>Malejąco ↓</button>
      </div>
      <input
        aria-label="Szukaj wartości"
        placeholder="Szukaj wartości…"
        value={szukaj}
        onChange={(e) => ustawSzukaj(e.target.value)}
      />
      <div className="rzad">
        <button onClick={() => ustawWybrane(wartosci.map((w) => w.wartosc))}>
          Zaznacz wszystkie
        </button>
        <button onClick={() => ustawWybrane([])}>Odznacz</button>
      </div>
      <div className="wartosci">
        {widoczne.map((w) => (
          <label key={JSON.stringify(w.wartosc)} className="checkbox">
            <input
              type="checkbox"
              checked={wybrane.includes(w.wartosc)}
              onChange={(e) =>
                ustawWybrane(
                  e.target.checked
                    ? [...wybrane, w.wartosc]
                    : wybrane.filter((x) => x !== w.wartosc),
                )
              }
            />
            <span>
              {w.wartosc === null ? "(Puste)" : pokazWartosc(w.wartosc)}
            </span>
            <small>{w.liczba}</small>
          </label>
        ))}
      </div>
      {zakres && (
        <div className="rzad">
          <label>
            Od
            <input
              type={
                pole === "interwal" || pole === "liczba_qr" ? "number" : "date"
              }
              value={od}
              onChange={(e) => ustawOd(e.target.value)}
            />
          </label>
          <label>
            Do
            <input
              type={
                pole === "interwal" || pole === "liczba_qr" ? "number" : "date"
              }
              value={doDaty}
              onChange={(e) => ustawDo(e.target.value)}
            />
          </label>
        </div>
      )}
      <div className="rzad">
        <button onClick={() => zatwierdz(null)}>Wyczyść</button>
        <button
          className="glowny"
          onClick={() => zatwierdz({ wartosci: wybrane, od, do: doDaty })}
        >
          Zastosuj
        </button>
      </div>
    </div>,
    document.body,
  );
}

/** Edytuje jedną komórkę po zatwierdzeniu; odrzucona zmiana nie nadpisuje wartości serwera. */
function Komorka({
  rekord,
  pole,
  edytowalna,
  zapisz,
  podpowiedzi,
}: {
  rekord: Rekord;
  pole: string;
  edytowalna: boolean;
  zapisz: (r: Rekord, p: string, v: Wartosc) => Promise<void>;
  podpowiedzi: string[];
}): React.ReactElement {
  const [edycja, ustawEdycje] = useState(false);
  const [wartosc, ustawWartosc] = useState(String(rekord[pole] ?? ""));
  const [zapis, ustawZapis] = useState(false);
  const [dostepnePodpowiedzi, ustawDostepnePodpowiedzi] = useState(podpowiedzi);
  useEffect(() => {
    if (!edycja || !["typ", "wydzial"].includes(pole)) return;
    let aktywne = true;
    wywolajApi<{ wartosci: { wartosc: Wartosc; liczba: number }[] }>(
      "/api/wartosci/" + pole,
      "POST",
      {},
    )
      .then((d) => {
        if (aktywne)
          ustawDostepnePodpowiedzi(
            d.wartosci
              .filter((w) => w.wartosc !== null)
              .map((w) => String(w.wartosc)),
          );
      })
      .catch(() => {});
    return () => {
      aktywne = false;
    };
  }, [edycja, pole]);
  /** Zapisuje nową wartość po Enter lub utracie fokusu i kończy edycję dopiero po sukcesie. */
  async function zatwierdz(): Promise<void> {
    if (zapis) return;
    const nowa = pole === "interwal" ? Number(wartosc) : wartosc || null;
    if (nowa === rekord[pole] || String(rekord[pole] ?? "") === wartosc) {
      ustawEdycje(false);
      return;
    }
    ustawZapis(true);
    try {
      await zapisz(rekord, pole, nowa);
      ustawEdycje(false);
    } finally {
      ustawZapis(false);
    }
  }
  if (!edycja)
    return (
      <button
        className={"komorka " + (edytowalna ? "edytowalna" : "")}
        disabled={!edytowalna}
        onClick={() => {
          ustawWartosc(String(rekord[pole] ?? ""));
          ustawEdycje(true);
        }}
        title={edytowalna ? "Kliknij, aby edytować" : undefined}
      >
        {pole === "dopuszczenie" ? (
          <span
            className={rekord[pole] ? "etykieta zielona" : "etykieta czerwona"}
          >
            {pokazWartosc(rekord[pole])}
          </span>
        ) : pole === "metrologiczny" ? (
          <span
            className={
              "etykieta " +
              (rekord[pole] === "Termin przekroczony" ? "czerwona" : "szara")
            }
          >
            {pokazWartosc(rekord[pole])}
          </span>
        ) : (
          pokazWartosc(rekord[pole])
        )}
      </button>
    );
  const wspolne = {
    autoFocus: true,
    disabled: zapis,
    value: wartosc,
    onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
      ustawWartosc(e.target.value),
    onBlur: () => {
      void zatwierdz().catch(() => {});
    },
    onKeyDown: (e: React.KeyboardEvent) => {
      if (e.key === "Enter") void zatwierdz().catch(() => {});
      if (e.key === "Escape") ustawEdycje(false);
    },
    "aria-label": `Edytuj ${pole}`,
  };
  return SLOWNIKI[pole] ? (
    <select {...wspolne}>
      {SLOWNIKI[pole].map((v) => (
        <option key={v}>{v}</option>
      ))}
    </select>
  ) : (
    <>
      <input
        {...wspolne}
        type={
          pole === "ostatni" || pole === "nastepny"
            ? "date"
            : pole === "interwal"
              ? "number"
              : "text"
        }
        list={"slownik-" + pole + "-" + rekord.id}
      />
      <datalist id={"slownik-" + pole + "-" + rekord.id}>
        {dostepnePodpowiedzi.map((v) => (
          <option key={v} value={v} />
        ))}
      </datalist>
    </>
  );
}

/** Pokazuje historię z tej samej bazy, bez tworzenia nowego odczytu QR. */
function Historia({
  adres,
  zamknij,
  pominCzas,
}: {
  adres: string;
  zamknij?: () => void;
  pominCzas?: string;
}): React.ReactElement {
  const [strona, ustawStrone] = useState(1);
  const [dane, ustawDane] = useState<{
    wpisy: { czas: string; status: string; dopuszczenie: boolean }[];
    dalej: boolean;
  }>();
  const [blad, ustawBlad] = useState("");
  useEffect(() => {
    let aktualne = true;
    wywolajApi<typeof dane>(`${adres}?strona=${strona}`)
      .then((d) => {
        if (aktualne) ustawDane(d);
      })
      .catch((b) => {
        if (aktualne) ustawBlad(b.message);
      });
    return () => {
      aktualne = false;
    };
  }, [adres, strona]);
  const wpisy =
    dane?.wpisy.filter(
      (w) =>
        !pominCzas ||
        new Date(w.czas).getTime() < new Date(pominCzas).getTime(),
    ) ?? [];
  return (
    <section className="karta historia">
      <div className="rzad">
        <h2>Historia odczytów QR</h2>
        {zamknij && <button onClick={zamknij}>Zamknij</button>}
      </div>
      <p className="pomoc">
        Odczyt karty nie potwierdza fizycznego sprawdzenia przyrządu.
      </p>
      {blad && <p role="alert">{blad}</p>}
      {wpisy.map((w, i) => (
        <div key={w.czas + i} className="wpis">
          <time>{pokazWartosc(w.czas)}</time>
          <span>{w.status}</span>
          <strong>{w.dopuszczenie ? "Dopuszczony" : "Zablokowany"}</strong>
        </div>
      ))}
      {dane && wpisy.length === 0 && <p>Brak wcześniejszych odczytów.</p>}
      <div className="rzad">
        <button disabled={strona === 1} onClick={() => ustawStrone(strona - 1)}>
          Poprzednia
        </button>
        <span>Strona {strona}</span>
        <button disabled={!dane?.dalej} onClick={() => ustawStrone(strona + 1)}>
          Następna
        </button>
      </div>
    </section>
  );
}

/** Wyświetla publiczną kartę i automatycznie rejestruje otwarcie, z ponowieniem o tym samym UUID. */
function KartaPubliczna(): React.ReactElement {
  const token = location.pathname.split("/")[2];
  const [dane, ustawDane] = useState<{ czas: string; przyrzad: Rekord }>();
  const [blad, ustawBlad] = useState("");
  const zdarzenie = useRef(crypto.randomUUID());
  const trwa = useRef(false);
  /** Rejestruje widoczne otwarcie; błąd zachowuje UUID, powrót z pamięci historii tworzy nowy odczyt. */
  const otworz = useCallback(
    async (nowe = false): Promise<void> => {
      if (document.visibilityState !== "visible" || trwa.current) return;
      trwa.current = true;
      if (nowe) zdarzenie.current = crypto.randomUUID();
      ustawBlad("");
      try {
        ustawDane(
          await wywolajApi(
            "/public/otwarcie/" + encodeURIComponent(token),
            "POST",
            { zdarzenie: zdarzenie.current },
          ),
        );
      } catch (b) {
        ustawBlad((b as Error).message);
      } finally {
        trwa.current = false;
      }
    },
    [token],
  );
  useEffect(() => {
    /** Rejestruje odczyt po przywróceniu strony z pamięci nawigacji. */
    function przywrocono(e: PageTransitionEvent): void {
      if (e.persisted) void otworz(true);
    }
    /** Czeka na pierwszą widoczność otwartej w tle karty. */
    function pokazano(): void {
      if (!dane) void otworz();
    }
    void otworz();
    window.addEventListener("pageshow", przywrocono);
    document.addEventListener("visibilitychange", pokazano);
    return () => {
      window.removeEventListener("pageshow", przywrocono);
      document.removeEventListener("visibilitychange", pokazano);
    };
  }, [otworz]);
  return (
    <>
      <Naglowek />
      <main className="publiczna">
        <span className="nadtytul">KARTA PRZYRZĄDU</span>
        {blad ? (
          <section className="karta">
            <p className="blad" role="alert">
              {blad}
            </p>
            <button onClick={() => void otworz()}>Spróbuj ponownie</button>
          </section>
        ) : !dane ? (
          <p>Odczytywanie aktualnego statusu…</p>
        ) : (
          <>
            <h1>{dane.przyrzad.numer}</h1>
            <p>{dane.przyrzad.typ}</p>
            <div
              className={
                "decyzja " + (dane.przyrzad.dopuszczenie ? "tak" : "nie")
              }
            >
              <small>DOPUSZCZENIE DO UŻYTKOWANIA</small>
              <strong>
                {dane.przyrzad.dopuszczenie ? "Dopuszczony" : "Zablokowany"}
              </strong>
              <span>{dane.przyrzad.metrologiczny}</span>
            </div>
            <p>Odczyt: {pokazWartosc(dane.czas)}</p>
            <dl className="szczegoly">
              {KOLUMNY.filter(
                ([p]) => !["rr", "numer", "dopuszczenie"].includes(p),
              ).map(([pole, etykieta]) => (
                <div key={pole}>
                  <dt>{etykieta}</dt>
                  <dd>{pokazWartosc(dane.przyrzad[pole])}</dd>
                </div>
              ))}
            </dl>
            <Historia
              key={dane.czas}
              pominCzas={dane.czas}
              adres={"/public/historia/" + encodeURIComponent(token)}
            />
          </>
        )}
      </main>
    </>
  );
}

/** Udostępnia właściwy rejestr, filtry, edycję, eksport i archiwum zgodnie z rolą sesji. */
function Ewidencja({
  sesja,
  wyloguj,
}: {
  sesja: Sesja;
  wyloguj: () => void;
}): React.ReactElement {
  const [rekordy, ustawRekordy] = useState<Rekord[]>([]);
  const [liczba, ustawLiczbe] = useState(0);
  const [filtry, ustawFiltry] = useState<Filtry>({});
  const [strona, ustawStrone] = useState(1);
  const [sortuj, ustawSortuj] = useState("numer");
  const [malejaco, ustawMalejaco] = useState(false);
  const [archiwum, ustawArchiwum] = useState(false);
  const [blad, ustawBlad] = useState("");
  const [oczekiwanie, ustawOczekiwanie] = useState(true);
  const [odswiez, ustawOdswiez] = useState(0);
  const [filtrPola, ustawFiltrPola] = useState<string | null>(null);
  const [wartosci, ustawWartosci] = useState<
    { wartosc: Wartosc; liczba: number }[]
  >([]);
  const [historia, ustawHistorie] = useState<string | null>(null);
  const [zarzadzanieKontami, ustawZarzadzanieKontami] = useState(false);
  const [modal, ustawModal] = useState<"nowy" | "czynnosc" | null>(null);
  const [wybrany, ustawWybranego] = useState<Rekord | null>(null);
  const [potwierdzenie, ustawPotwierdzenie] = useState<{
    r: Rekord;
    operacja: "usun" | "qr";
  } | null>(null);
  const zapytanie = useMemo(
    () => ({ filtry, strona, rozmiar: 50, sortuj, malejaco, archiwum }),
    [filtry, strona, sortuj, malejaco, archiwum],
  );
  useEffect(() => {
    let aktywne = true;
    ustawOczekiwanie(true);
    wywolajApi<{ rekordy: Rekord[]; liczba: number }>(
      "/api/przyrzady/szukaj",
      "POST",
      zapytanie,
    )
      .then((d) => {
        if (aktywne) {
          ustawRekordy(d.rekordy);
          ustawLiczbe(d.liczba);
          ustawBlad("");
        }
      })
      .catch((b) => {
        if (aktywne) ustawBlad(b.message);
      })
      .finally(() => {
        if (aktywne) ustawOczekiwanie(false);
      });
    return () => {
      aktywne = false;
    };
  }, [zapytanie, odswiez]);
  /** Pobiera pełne podpowiedzi kolumny przy aktywnych filtrach pozostałych kolumn. */
  async function otworzFiltr(pole: string): Promise<void> {
    try {
      const w = await wywolajApi<{
        wartosci: { wartosc: Wartosc; liczba: number }[];
      }>("/api/wartosci/" + pole, "POST", zapytanie);
      ustawWartosci(w.wartosci);
      ustawFiltrPola(pole);
    } catch (b) {
      ustawBlad((b as Error).message);
    }
  }
  /** Wysyła zmianę jednej komórki z wersją; w konflikcie wymusza ponowne pobranie, nie nadpisuje serwera. */
  const zapisz = useCallback(
    async (r: Rekord, pole: string, wartosc: Wartosc): Promise<void> => {
      let uzasadnienie = "";
      if (pole === "nastepny" || pole === "klasa") {
        uzasadnienie = window.prompt("Podaj uzasadnienie zmiany") || "";
        if (!uzasadnienie) return;
      }
      try {
        await wywolajApi("/api/przyrzady/" + r.id, "PATCH", {
          wersja: r.wersja,
          zmiany: { [pole]: wartosc },
          uzasadnienie,
        });
        ustawOdswiez((v) => v + 1);
      } catch (b) {
        ustawBlad((b as Error).message);
        ustawOdswiez((v) => v + 1);
        throw b;
      }
    },
    [],
  );
  /** Wykonuje potwierdzoną archiwizację albo rotację tokenu, bez tworzenia odczytu QR. */
  async function wykonajPotwierdzona(): Promise<void> {
    if (!potwierdzenie) return;
    try {
      const { r, operacja } = potwierdzenie;
      if (operacja === "usun") await zapisz(r, "usuniety", !archiwum);
      else {
        await wywolajApi("/api/przyrzady/" + r.id + "/qr", "POST", {
          wersja: r.wersja,
          zmiany: {},
        });
        ustawOdswiez((v) => v + 1);
      }
      ustawPotwierdzenie(null);
    } catch (b) {
      ustawBlad((b as Error).message);
    }
  }
  /** Zapisuje formularz nowego przyrządu lub rzeczywistej czynności metrologicznej. */
  async function zapiszFormularz(
    e: React.FormEvent<HTMLFormElement>,
  ): Promise<void> {
    e.preventDefault();
    const d = Object.fromEntries(new FormData(e.currentTarget));
    try {
      if (modal === "nowy") await wywolajApi("/api/przyrzady", "POST", d);
      else if (wybrany)
        await wywolajApi(
          "/api/przyrzady/" + wybrany.id + "/czynnosci",
          "POST",
          { ...d, wersja: wybrany.wersja },
        );
      ustawModal(null);
      ustawOdswiez((v) => v + 1);
    } catch (b) {
      ustawBlad((b as Error).message);
    }
  }
  /** Pobiera plik XLSX z wybranym zakresem i uruchamia pobranie, zachowując cookies oraz CSRF. */
  async function eksportuj(cale: boolean): Promise<void> {
    try {
      const odp = await fetch("/api/eksport", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": tokenCsrf,
        },
        body: JSON.stringify({ ...zapytanie, filtry: cale ? {} : filtry }),
      });
      if (!odp.ok) throw new Error("Nie udało się wygenerować eksportu");
      const url = URL.createObjectURL(await odp.blob());
      const a = document.createElement("a");
      a.href = url;
      a.download = "aunde-metrologia.xlsx";
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (b) {
      ustawBlad((b as Error).message);
    }
  }
  const kolumny = useMemo<ColumnDef<Rekord>[]>(
    () => [
      {
        id: "lp",
        header: "Lp",
        cell: ({ row }) => (strona - 1) * 50 + row.index + 1,
      },
      ...KOLUMNY.filter(
        ([pole]) => pole !== "rr" || sesja.rola === "Administrator",
      ).map(([pole, nazwa]) => ({
        accessorKey: pole,
        header: () => (
          <button
            className={"naglowek-kolumny " + (filtry[pole] ? "aktywny" : "")}
            onClick={() => void otworzFiltr(pole)}
          >
            {nazwa}
            <span>⌄</span>
          </button>
        ),
        cell: ({ row }: { row: { original: Rekord } }) => (
          <Komorka
            key={row.original.id + pole + row.original.wersja}
            rekord={row.original}
            pole={pole}
            zapisz={zapisz}
            podpowiedzi={[
              ...new Set(rekordy.map((r) => String(r[pole] ?? ""))),
            ]}
            edytowalna={
              !archiwum &&
              sesja.rola !== "Viewer" &&
              ![
                "numer",
                "metrologiczny",
                "dopuszczenie",
                "komentarz_dat",
                "ostatni_qr",
                "liczba_qr",
              ].includes(pole) &&
              ((pole !== "rr" && pole !== "nastepny") ||
                sesja.rola === "Administrator")
            }
          />
        ),
      })),
      {
        id: "akcje",
        header: "Operacje",
        cell: ({ row }) => (
          <div className="akcje">
            <button onClick={() => ustawHistorie(row.original.id)}>
              Historia QR
            </button>
            {sesja.rola !== "Viewer" && !archiwum && (
              <button
                onClick={() => {
                  ustawWybranego(row.original);
                  ustawModal("czynnosc");
                }}
              >
                Zapisz czynność
              </button>
            )}
            {sesja.rola === "Administrator" && (
              <>
                <button
                  onClick={() =>
                    ustawPotwierdzenie({ r: row.original, operacja: "qr" })
                  }
                >
                  Nowy QR
                </button>
                <button
                  aria-label={archiwum ? "Przywróć" : "Usuń"}
                  onClick={() =>
                    ustawPotwierdzenie({ r: row.original, operacja: "usun" })
                  }
                >
                  {archiwum ? "Przywróć" : "🗑 Usuń"}
                </button>
              </>
            )}
          </div>
        ),
      },
    ],
    [rekordy, sesja.rola, filtry, strona, archiwum, zapisz, zapytanie],
  );
  const tabela = useReactTable({
    data: rekordy,
    columns: kolumny,
    getCoreRowModel: getCoreRowModel(),
    manualPagination: true,
    manualFiltering: true,
    manualSorting: true,
  });
  return (
    <>
      <Naglowek sesja={sesja} wyloguj={wyloguj} />
      <main className="rejestr">
        <div className="tytul-rzad">
          <div>
            <span className="nadtytul">JAKOŚĆ / NADZÓR METROLOGICZNY</span>
            <h1>{archiwum ? "Archiwum przyrządów" : "Ewidencja przyrządów"}</h1>
            <p>Terminy, przydziały i aktualne dopuszczenie do użytkowania.</p>
          </div>
          {sesja.rola === "Administrator" && (
            <button className="glowny" onClick={() => ustawModal("nowy")}>
              + Dodaj przyrząd
            </button>
          )}
        </div>
        <div className="narzedzia">
          <strong>
            {liczba.toLocaleString("pl-PL")} <span>rekordów</span>
          </strong>
          <button
            onClick={() => {
              ustawFiltry({});
              ustawStrone(1);
            }}
          >
            Wyczyść filtry ({Object.keys(filtry).length})
          </button>
          <button onClick={() => ustawOdswiez((v) => v + 1)}>Odśwież</button>
          {sesja.rola === "Administrator" && (
            <>
              <label className="checkbox">
                <input
                  type="checkbox"
                  checked={archiwum}
                  onChange={(e) => {
                    ustawArchiwum(e.target.checked);
                    ustawStrone(1);
                  }}
                />
                Archiwum
              </label>
              <div className="odstep" />
              <button onClick={() => void eksportuj(false)}>
                Eksport wyników
              </button>
              <button onClick={() => void eksportuj(true)}>
                Eksport całości
              </button>
              <button onClick={() => ustawZarzadzanieKontami(true)}>
                Zarządzaj kontami
              </button>
            </>
          )}
        </div>
        {blad && (
          <div className="blad" role="alert">
            {blad}
            <button onClick={() => ustawBlad("")}>Zamknij</button>
          </div>
        )}
        <div className="tabela-ramka" aria-busy={oczekiwanie}>
          <table>
            <thead>
              {tabela.getHeaderGroups().map((g) => (
                <tr key={g.id}>
                  {g.headers.map((h) => (
                    <th key={h.id}>
                      {flexRender(h.column.columnDef.header, h.getContext())}
                      {h.column.id === filtrPola && (
                        <FiltrKolumny
                          pole={filtrPola}
                          filtr={filtry[filtrPola] || {}}
                          wartosci={wartosci}
                          zamknij={() => ustawFiltrPola(null)}
                          sortuj={(m) => {
                            ustawSortuj(filtrPola);
                            ustawMalejaco(m);
                            ustawFiltrPola(null);
                          }}
                          zatwierdz={(f) => {
                            const nowe = { ...filtry };
                            if (f) nowe[filtrPola] = f;
                            else delete nowe[filtrPola];
                            ustawFiltry(nowe);
                            ustawStrone(1);
                            ustawFiltrPola(null);
                          }}
                        />
                      )}
                    </th>
                  ))}
                </tr>
              ))}
            </thead>
            <tbody>
              {tabela.getRowModel().rows.map((r) => (
                <tr key={r.original.id}>
                  {r.getVisibleCells().map((c) => (
                    <td key={c.id}>
                      {flexRender(c.column.columnDef.cell, c.getContext())}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          {!oczekiwanie && !rekordy.length && (
            <div className="pusto">
              <h2>Brak przyrządów w tym widoku</h2>
              <p>
                Zmień filtry albo dodaj przyrząd. Import źródłowy wykonuje
                administrator IT.
              </p>
            </div>
          )}
        </div>
        <footer className="paginacja">
          <span>
            {oczekiwanie
              ? "Pobieranie…"
              : `Strona ${strona} z ${Math.max(1, Math.ceil(liczba / 50))}`}
          </span>
          <button
            disabled={strona === 1 || oczekiwanie}
            onClick={() => ustawStrone(strona - 1)}
          >
            ← Poprzednia
          </button>
          <button
            disabled={strona * 50 >= liczba || oczekiwanie}
            onClick={() => ustawStrone(strona + 1)}
          >
            Następna →
          </button>
        </footer>
        <p className="pomoc">
          Kliknij nagłówek, aby filtrować lub sortować. Kliknij dostępną
          komórkę, aby ją edytować. Daty i godziny zdarzeń: Europe/Warsaw.
        </p>
      </main>
      {historia && (
        <div className="nakladka">
          <Historia
            adres={"/api/przyrzady/" + historia + "/historia"}
            zamknij={() => ustawHistorie(null)}
          />
        </div>
      )}
      {potwierdzenie && (
        <div className="nakladka">
          <section className="karta" role="dialog" aria-label="Potwierdzenie">
            <h2>
              {potwierdzenie.operacja === "qr"
                ? "Unieważnić poprzedni kod QR?"
                : archiwum
                  ? "Przywrócić przyrząd?"
                  : "Przenieść do archiwum?"}
            </h2>
            <p>{potwierdzenie.r.numer}</p>
            <div className="rzad">
              <button onClick={() => ustawPotwierdzenie(null)}>Anuluj</button>
              <button
                className="glowny"
                onClick={() => void wykonajPotwierdzona()}
              >
                Potwierdź
              </button>
            </div>
          </section>
        </div>
      )}
      {zarzadzanieKontami && (
        <div className="nakladka">
          <Konta zamknij={() => ustawZarzadzanieKontami(false)} />
        </div>
      )}
      {modal && (
        <div className="nakladka">
          <form className="karta" onSubmit={zapiszFormularz} role="dialog">
            <div className="rzad">
              <h2>
                {modal === "nowy"
                  ? "Nowy przyrząd"
                  : "Zapis rzeczywistej czynności"}
              </h2>
              <button type="button" onClick={() => ustawModal(null)}>
                Zamknij
              </button>
            </div>
            {modal === "nowy" ? (
              <>
                <label>
                  Numer
                  <input name="numer" required maxLength={500} />
                </label>
                <label>
                  Typ
                  <input name="typ" required maxLength={150} />
                </label>
                <label>
                  Wydział bez ulicy
                  <input name="wydzial" required maxLength={150} />
                </label>
                <p>
                  Nowy przyrząd: grupa B, nieaktywny, stan techniczny
                  nieustalony.
                </p>
              </>
            ) : (
              <>
                <p>
                  {wybrany?.numer}:{" "}
                  {wybrany?.klasa === "A" ? "wzorcowanie" : "sprawdzenie"}
                </p>
                <label>
                  Data wykonania
                  <input type="date" name="data" required />
                </label>
                <label>
                  Wynik
                  <select name="wynik">
                    <option>Pozytywny</option>
                    <option>Negatywny</option>
                  </select>
                </label>
                <label>
                  Numer świadectwa / raportu
                  <input
                    name="numer_swiadectwa"
                    required={wybrany?.klasa === "A"}
                  />
                </label>
                <label>
                  Uwagi
                  <textarea name="uwagi" />
                </label>
              </>
            )}
            <button className="glowny">Zapisz</button>
            {blad && (
              <p className="blad" role="alert">
                {blad}
              </p>
            )}
          </form>
        </div>
      )}
    </>
  );
}

/** Odtwarza sesję z serwera i przełącza widok bez utrwalania sekretów w przeglądarce. */
function Aplikacja(): React.ReactElement {
  const [sesja, ustawSesje] = useState<Sesja | null>(null);
  const [sprawdzono, ustawSprawdzono] = useState(false);
  /** Zapamiętuje sesję i token wyłącznie w pamięci aplikacji. */
  function przyjmijSesje(s: Sesja): void {
    ustawCsrf(s.csrf);
    ustawSesje(s);
  }
  /** Kończy sesję po stronie serwera, następnie usuwa dane konta z pamięci. */
  async function wyloguj(): Promise<void> {
    try {
      await wywolajApi("/api/wylogowanie", "POST");
    } finally {
      ustawCsrf("");
      ustawSesje(null);
    }
  }
  useEffect(() => {
    if (location.pathname.startsWith("/p/")) {
      ustawSprawdzono(true);
      return;
    }
    wywolajApi<Sesja>("/api/sesja")
      .then(przyjmijSesje)
      .catch(() => {})
      .finally(() => ustawSprawdzono(true));
  }, []);
  if (location.pathname.startsWith("/p/")) return <KartaPubliczna />;
  if (!sprawdzono) return <p className="oczekiwanie">Sprawdzanie sesji…</p>;
  return sesja ? (
    <Ewidencja sesja={sesja} wyloguj={() => void wyloguj()} />
  ) : (
    <Logowanie gotowe={przyjmijSesje} />
  );
}

createRoot(document.getElementById("root")!).render(<Aplikacja />);
