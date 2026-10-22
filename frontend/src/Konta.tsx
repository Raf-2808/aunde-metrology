import React, { useEffect, useState } from "react";
import { wywolajApi } from "./api";
type Konto = { id: string; login: string; rola: string; aktywny: boolean };

/** Pozwala Administratorowi dodawać i wyłączać konta, zmieniać role i hasła; nigdy nie odczytuje haseł. */
export function Konta({
  zamknij,
}: {
  zamknij: () => void;
}): React.ReactElement {
  const [konta, ustawKonta] = useState<Konto[]>([]);
  const [blad, ustawBlad] = useState("");
  const [wybrane, ustawWybrane] = useState<Konto | null>(null);
  const [zapis, ustawZapis] = useState(false);
  /** Odczytuje aktualne role i aktywność, bez informacji uwierzytelniających. */
  async function odswiez(): Promise<void> {
    ustawKonta(await wywolajApi<Konto[]>("/api/uzytkownicy"));
  }
  useEffect(() => {
    void odswiez().catch((b) => ustawBlad(b.message));
  }, []);
  /** Zapisuje jawnie wybrane zmiany; backend chroni ostatniego Administratora i unieważnia sesje. */
  async function zmien(k: Konto, zmiana: object): Promise<void> {
    ustawZapis(true);
    ustawBlad("");
    try {
      await wywolajApi("/api/uzytkownicy/" + k.id, "PATCH", zmiana);
      await odswiez();
    } catch (b) {
      ustawBlad((b as Error).message);
    } finally {
      ustawZapis(false);
    }
  }
  /** Tworzy konto lub ustawia nowe hasło z pola typu password, bez wyświetlania go na liście. */
  async function zapiszFormularz(
    e: React.FormEvent<HTMLFormElement>,
  ): Promise<void> {
    e.preventDefault();
    const formularz = e.currentTarget;
    const dane = Object.fromEntries(new FormData(formularz));
    ustawZapis(true);
    ustawBlad("");
    try {
      if (wybrane)
        await wywolajApi("/api/uzytkownicy/" + wybrane.id, "PATCH", {
          haslo: dane.haslo,
        });
      else await wywolajApi("/api/uzytkownicy", "POST", dane);
      formularz.reset();
      ustawWybrane(null);
      await odswiez();
    } catch (b) {
      ustawBlad((b as Error).message);
    } finally {
      ustawZapis(false);
    }
  }
  return (
    <section className="karta" role="dialog" aria-label="Zarządzanie kontami">
      <div className="rzad">
        <h2>Konta użytkowników</h2>
        <button onClick={zamknij}>Zamknij</button>
      </div>
      {blad && (
        <p role="alert" className="blad">
          {blad}
        </p>
      )}
      <p className="pomoc">Zmiana konta unieważnia jego istniejące sesje.</p>
      {konta.map((k) => (
        <div className="wpis" key={k.id}>
          <strong>{k.login}</strong>
          <select
            aria-label={"Rola " + k.login}
            value={k.rola}
            disabled={zapis}
            onChange={(e) => void zmien(k, { rola: e.target.value })}
          >
            <option>Viewer</option>
            <option>Editor</option>
            <option>Administrator</option>
          </select>
          <button
            disabled={zapis}
            onClick={() => void zmien(k, { aktywny: !k.aktywny })}
          >
            {k.aktywny ? "Dezaktywuj" : "Aktywuj"}
          </button>
          <button disabled={zapis} onClick={() => ustawWybrane(k)}>
            Ustaw hasło
          </button>
        </div>
      ))}
      <form onSubmit={zapiszFormularz}>
        <h3>{wybrane ? "Nowe hasło: " + wybrane.login : "Dodaj konto"}</h3>
        {!wybrane && (
          <>
            <label>
              Login
              <input name="login" minLength={3} maxLength={150} required />
            </label>
            <label>
              Rola
              <select name="rola">
                <option>Viewer</option>
                <option>Editor</option>
                <option>Administrator</option>
              </select>
            </label>
          </>
        )}
        <label>
          Nowe hasło
          <input
            name="haslo"
            type="password"
            minLength={12}
            maxLength={300}
            required
            autoComplete="new-password"
          />
        </label>
        <div className="rzad">
          <button className="glowny" disabled={zapis}>
            Zapisz konto
          </button>
          {wybrane && (
            <button type="button" onClick={() => ustawWybrane(null)}>
              Anuluj zmianę hasła
            </button>
          )}
        </div>
      </form>
    </section>
  );
}
