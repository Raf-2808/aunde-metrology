export type Sesja = {
  login: string;
  rola: "Viewer" | "Editor" | "Administrator";
  csrf: string;
};
export type Wartosc = string | number | boolean | null;
export type Rekord = Record<string, Wartosc> & {
  id: string;
  numer: string;
  wersja: number;
};
export type Filtr = {
  wartosci?: Wartosc[];
  szukaj?: string;
  od?: string;
  do?: string;
  puste?: boolean;
};
export type Filtry = Record<string, Filtr>;
export let tokenCsrf = "";

/** Ustawia token CSRF sesji w pamięci, bez zapisu do localStorage. */
export function ustawCsrf(token: string): void {
  tokenCsrf = token;
}

/** Wywołuje API z cookie i CSRF, zwraca JSON albo polski błąd; nie loguje danych wejścia. */
export async function wywolajApi<T>(
  adres: string,
  metoda = "GET",
  dane?: unknown,
): Promise<T> {
  const wynik = await fetch(adres, {
    method: metoda,
    credentials: "same-origin",
    cache: "no-store",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": tokenCsrf },
    body: dane === undefined ? undefined : JSON.stringify(dane),
  });
  if (!wynik.ok) {
    const blad = await wynik.json().catch(() => ({}));
    throw new Error(
      typeof blad.detail === "string"
        ? blad.detail
        : "Nie udało się wykonać operacji",
    );
  }
  return wynik.json() as Promise<T>;
}

/** Formatuje datę/czas UTC w Europe/Warsaw, zachowuje samą datę metrologiczną. */
export function pokazWartosc(wartosc: Wartosc | undefined): string {
  if (wartosc === null || wartosc === undefined || wartosc === "")
    return "Brak";
  if (typeof wartosc === "boolean")
    return wartosc ? "Odblokowany" : "Zablokowany";
  if (typeof wartosc === "string" && /^\d{4}-\d{2}-\d{2}T/.test(wartosc))
    return new Intl.DateTimeFormat("pl-PL", {
      dateStyle: "short",
      timeStyle: "medium",
      timeZone: "Europe/Warsaw",
    }).format(new Date(wartosc));
  return String(wartosc);
}
