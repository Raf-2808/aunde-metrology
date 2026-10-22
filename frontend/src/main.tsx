import React, { useState, useEffect, useRef } from 'react';
import { createRoot } from 'react-dom/client';
import * as echarts from 'echarts';
import { api, ApiError, setCsrf } from './api';
import { Spec, Article, Order, Plan, LabResult, User, Method, inSpec, complete } from './types';
import './style.css';

const statuses: Record<string, string> = {
  WAITING: 'Oczekuje na badanie',
  IN_PROGRESS: 'W trakcie badania',
  TESTED: 'Zbadane',
  HELD: 'Wstrzymane',
};
const pages: Record<string, string> = {
  orders: 'Zlecenia badań',
  test: 'Nowe badanie',
  real: 'Wyniki rzeczywiste',
  simulated: 'Wyniki symulowane',
  recover: 'Przywołaj wyniki',
  spc: 'Analiza SPC',
  articles: 'Artykuły i metody',
  admin: 'Administracja',
};
const localDate = () => new Intl.DateTimeFormat('sv-SE').format(new Date());
const fmt = (v: string | null, d = 2) =>
  v === null
    ? 'Brak średniej'
    : Number(v).toLocaleString('pl-PL', { minimumFractionDigits: d, maximumFractionDigits: d });
const tolerance = (s: Spec) =>
  s.kind === 'numeric'
    ? `${s.lsl === null ? '' : `${s.lower_inclusive ? '≥' : '>'} ${s.lsl}`} ${s.usl === null ? '' : `${s.upper_inclusive ? '≤' : '<'} ${s.usl}`} ${s.unit}`
    : s.passing.join(', ');
const blankSpec = (): Spec => ({
  key: '',
  name: '',
  method_id: 0,
  unit: '',
  kind: 'numeric',
  count: 3,
  labels: ['LH', 'M', 'RH'],
  lsl: null,
  usl: null,
  lower_inclusive: true,
  upper_inclusive: true,
  decimals: 2,
  frequency: 'every',
  every_n: 10,
  allowed: [],
  passing: [],
  simulation_offset: null,
});

/** Formularz logowania korzysta wyłącznie z API uwierzytelniania. */
function Login({ done }: { done: (u: User) => void }) {
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  return (
    <main className="login">
      <div className="brand">
        AUNDE<span>LABORATORY SYSTEM</span>
      </div>
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          const f = new FormData(e.currentTarget);
          try {
            const u = await api<User>('/login', 'POST', Object.fromEntries(f));
            setCsrf(u.csrf);
            done(u);
          } catch (x) {
            setError(String(x));
          } finally {
            setBusy(false);
          }
        }}
      >
        <p className="eyebrow">AUNDE POLAND</p>
        <h1>Laboratorium pod kontrolą.</h1>
        <p>Zaloguj się do systemu badań i analizy jakości.</p>
        <label>
          Użytkownik
          <input name="login" autoComplete="username" required />
        </label>
        <label>
          Hasło
          <input name="password" type="password" autoComplete="current-password" required />
        </label>
        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
        <button disabled={busy}>Zaloguj się →</button>
        <small>Dostęp do wyników wymaga dodatkowego potwierdzenia hasła.</small>
      </form>
    </main>
  );
}

/** Obsługuje moduły, sesję i niezależne potwierdzanie chronionego dostępu. */
function App() {
  const [user, setUser] = useState<User | null>(null),
    [loading, setLoading] = useState(true),
    [page, setPage] = useState('orders'),
    [error, setError] = useState(''),
    [notice, setNotice] = useState('');
  const [articles, setArticles] = useState<Article[]>([]),
    [orders, setOrders] = useState<Order[]>([]),
    [methods, setMethods] = useState<Method[]>([]);
  const [source, setSource] = useState('real'),
    [scope, setScope] = useState<string | null>(null),
    [reauthPw, setReauthPw] = useState('');
  const [correction, setCorrection] = useState<{ id: number; reason: string } | null>(null);
  const [selectedOrder, setSelectedOrder] = useState<Order | null>(null),
    [plan, setPlan] = useState<Plan | null>(null),
    [values, setValues] = useState<Record<string, string[]>>({}),
    [ack, setAck] = useState(false),
    [saving, setSaving] = useState(false);
  const [records, setRecords] = useState<LabResult[]>([]),
    [detail, setDetail] = useState<LabResult | null>(null),
    [search, setSearch] = useState(''),
    [filter, setFilter] = useState(''),
    [start, setStart] = useState(''),
    [end, setEnd] = useState(''),
    [articleFilter, setArticleFilter] = useState(''),
    [sort, setSort] = useState(false);
  const [draft, setDraft] = useState<{ id?: number; code: string; name: string; specs: Spec[] }>({
    code: '',
    name: '',
    specs: [],
  });
  const [spcConfigs, setSpcConfigs] = useState<any[]>([]),
    [chart, setChart] = useState<any>(null),
    [chartId, setChartId] = useState('');
  const [notifications, setNotifications] = useState<any>({ rules: [], outbox: [] }),
    [audit, setAudit] = useState<any[]>([]),
    [users, setUsers] = useState<any[]>([]),
    [allSpecs, setAllSpecs] = useState<Spec[]>([]),
    [history, setHistory] = useState<any[]>([]);
  const can = (p: string) => user?.permissions.includes(p);
  /** Wykonuje operację z jawną obsługą błędów i wygaśnięcia autoryzacji. */
  async function run(fn: () => Promise<void>) {
    setError('');
    try {
      await fn();
    } catch (x) {
      if (x instanceof ApiError && x.status === 401) {
        setUser(null);
      } else if (x instanceof ApiError && x.status === 428) {
        setScope(page === 'spc' ? 'spc' : page === 'recover' ? source : page);
      } else setError(x instanceof Error ? x.message : String(x));
    }
  }
  async function refresh() {
    const [a, o, m] = await Promise.all([
      api<Article[]>('/articles'),
      api<Order[]>('/orders'),
      api<Method[]>('/methods'),
    ]);
    setArticles(a);
    setOrders(o);
    setMethods(m);
  }
  useEffect(() => {
    api<User>('/me')
      .then((u) => {
        setCsrf(u.csrf);
        setUser(u);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);
  useEffect(() => {
    if (user) void run(refresh);
  }, [user]);
  async function loadResults(src = page === 'recover' ? source : page) {
    const q = new URLSearchParams({
      lot: search,
      ...(start ? { start } : {}),
      ...(end ? { end } : {}),
      ...(articleFilter ? { article_id: articleFilter } : {}),
    });
    setRecords(await api<LabResult[]>(`/results/${src}?${q}`));
  }
  async function enter(p: string) {
    setPage(p);
    setError('');
    setNotice('');
    setDetail(null);
    setSearch('');
    setStart('');
    setEnd('');
    setArticleFilter('');
    setRecords([]);
    setHistory([]);
    setChart(null);
    if (['real', 'simulated', 'spc'].includes(p)) setScope(p);
  }
  async function authorize() {
    await api('/reauth', 'POST', { password: reauthPw, scope });
    setReauthPw('');
    const s = scope;
    setScope(null);
    if (s === 'real' || s === 'simulated') await loadResults(s);
    if (s === 'spc') setSpcConfigs(await api<any[]>('/spc/configs'));
  }
  async function begin(o: Order) {
    setCorrection(null);
    setPlan(null);
    setValues({});
    setAck(false);
    const p = await api<Plan>(`/orders/${o.id}/start`, 'POST');
    setSelectedOrder(o);
    setPlan(p);
    setValues(Object.fromEntries(p.specs.map((s) => [s.key, Array(s.count).fill('')])));
    setPage('test');
    await refresh();
  }
  async function save(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!selectedOrder || !plan || saving) return;
    setSaving(true);
    const f = Object.fromEntries(new FormData(e.currentTarget));
    if (!f.started_on) delete f.started_on;
    if (!f.ended_on) delete f.ended_on;
    try {
      await run(async () => {
        const r = await api<{ id: number; ok: boolean }>('/sessions', 'POST', {
          ...f,
          order_id: selectedOrder.id,
          cycle: plan.cycle,
          config_id: plan.config_id,
          values,
          acknowledged: ack,
          ...(correction ? { correction_of: correction.id, reason: correction.reason } : {}),
        });
        setNotice(`Zapisano sesję #${r.id}. Ocena: ${r.ok ? 'OK' : 'NOK'}.`);
        setPlan(null);
        setSelectedOrder(null);
        setPage('orders');
        await refresh();
      });
    } finally {
      setSaving(false);
    }
  }
  async function changeDisposition(o: Order) {
    const reason = window.prompt(
      o.status === 'HELD' ? 'Uzasadnienie cofnięcia wstrzymania' : 'Powód wstrzymania partii',
    );
    if (!reason) return;
    await api(`/orders/${o.id}/disposition`, 'POST', { held: o.status !== 'HELD', reason });
    await refresh();
  }
  async function loadDraft(id: string, copy = false) {
    if (!id) {
      setDraft({ code: '', name: '', specs: [] });
      return;
    }
    const a = articles.find((x) => x.id === Number(id))!;
    const c = await api<{ specs: Spec[] }>(`/articles/${id}/config`);
    setDraft({
      id: copy ? undefined : a.id,
      code: copy ? '' : a.code,
      name: copy ? '' : a.name,
      specs: c.specs,
    });
  }
  function patchSpec(i: number, patch: Partial<Spec>) {
    setDraft((d) => ({ ...d, specs: d.specs.map((s, j) => (i === j ? { ...s, ...patch } : s)) }));
  }
  async function adminLoad() {
    setNotifications(await api('/notifications'));
    setAudit(await api<any[]>('/audit'));
    if (can('users')) setUsers(await api<any[]>('/users'));
    const c = await Promise.all(
      articles.map((a) => api<{ specs: Spec[] }>(`/articles/${a.id}/config`)),
    );
    setAllSpecs(c.flatMap((x) => x.specs));
  }
  const warning = plan?.specs.some((s) => {
    const vs = values[s.key] || [];
    if (!vs.every((x) => x !== '')) return false;
    return s.kind === 'numeric'
      ? vs.some((x) => !inSpec(Number(x.replace(',', '.')), s))
      : vs.some((x) => !s.passing.includes(x));
  });
  const filteredOrders = orders.filter(
    (o) =>
      (!filter || o.status === filter) &&
      `${o.lot} ${o.article} ${o.code}`.toLowerCase().includes(search.toLowerCase()),
  );
  if (loading) return <div className="loading">Ładowanie systemu…</div>;
  if (!user) return <Login done={setUser} />;
  return (
    <div className="shell">
      <aside>
        <div className="brand">
          AUNDE<span>LABORATORY SYSTEM</span>
        </div>
        <p className="navlabel">PRACA LABORATORIUM</p>
        <nav>
          {Object.entries(pages)
            .filter(
              ([k]) =>
                k === 'orders' ||
                (k === 'recover' && (can('real') || can('simulated'))) ||
                (k === 'test' && can('test')) ||
                (k === 'articles' && can('configure')) ||
                (k === 'admin' && can('configure')) ||
                can(k),
            )
            .map(([k, v], i) => (
              <button
                key={k}
                className={page === k ? 'active' : ''}
                onClick={() =>
                  void run(async () => {
                    await enter(k);
                    if (k === 'admin') await adminLoad();
                  })
                }
              >
                <span className="navicon">{['▦', '＋', '▤', '◈', '↶', '⌁', '▣', '⚙'][i]}</span>
                {v}
              </button>
            ))}
        </nav>
        <div className="sidebarbottom">
          <strong>{user.login}</strong>
          <small>{user.role}</small>
          <button
            onClick={() =>
              void run(async () => {
                await api('/logout', 'POST');
                setUser(null);
                setRecords([]);
              })
            }
          >
            Wyloguj
          </button>
        </div>
      </aside>
      <section className="workspace">
        <header>
          <span>
            Laboratorium <b>/</b> {pages[page]}
          </span>
          <span className="date">
            {new Date().toLocaleDateString('pl-PL', {
              day: 'numeric',
              month: 'long',
              year: 'numeric',
            })}
          </span>
        </header>
        <main className="content">
          <div className="heading">
            <div>
              <p className="eyebrow">ZARZĄDZANIE JAKOŚCIĄ</p>
              <h1>{pages[page]}</h1>
              <p>
                {page === 'orders'
                  ? 'Kolejka próbek, przebieg badań i dyspozycje partii.'
                  : page === 'test'
                    ? 'Wszystkie wymagane pomiary w jednym formularzu.'
                    : page === 'spc'
                      ? 'Stabilność procesu na podstawie zatwierdzonych wyników rzeczywistych.'
                      : 'Centralny rejestr laboratoryjny AUNDE Poland.'}
              </p>
            </div>
            <span className="connection">
              <i /> Połączono z API
            </span>
          </div>
          {error && (
            <div className="error" role="alert">
              {error}
              <button className="text" onClick={() => setError('')}>
                Zamknij
              </button>
            </div>
          )}
          {notice && (
            <div className="success" role="status">
              {notice}
            </div>
          )}
          {page === 'orders' && (
            <>
              <div className="metrics">
                {Object.entries(statuses).map(([k, v]) => (
                  <button
                    key={k}
                    onClick={() => setFilter(filter === k ? '' : k)}
                    className={filter === k ? 'selected' : ''}
                  >
                    <span>{v}</span>
                    <strong>
                      {orders
                        .filter((o) => o.status === k)
                        .length.toString()
                        .padStart(2, '0')}
                    </strong>
                    <small>{k === 'HELD' ? 'Dyspozycja partii' : 'Zlecenia laboratoryjne'}</small>
                  </button>
                ))}
              </div>
              {can('order') && (
                <details className="panel">
                  <summary>＋ Zgłoś nowe lotto</summary>
                  <form
                    className="inlineform"
                    onSubmit={(e) => {
                      e.preventDefault();
                      const f = e.currentTarget,
                        d = Object.fromEntries(new FormData(f));
                      void run(async () => {
                        await api('/orders', 'POST', {
                          ...d,
                          article_id: Number(d.article_id),
                          required_sessions: Number(d.required_sessions || 1),
                          extra: String(d.extra || '')
                            .split(',')
                            .map((s) => s.trim())
                            .filter(Boolean),
                        });
                        f.reset();
                        await refresh();
                        setNotice('Dodano lotto do kolejki badań.');
                      });
                    }}
                  >
                    <label>
                      Artykuł
                      <select name="article_id" required>
                        <option value="">Wybierz artykuł</option>
                        {articles.map((a) => (
                          <option key={a.id} value={a.id}>
                            {a.code} · {a.name}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label>
                      Numer lotto
                      <input name="lot" required maxLength={120} />
                    </label>
                    <label>
                      Numer beli
                      <input name="roll" />
                    </label>
                    <label>
                      Ilość
                      <input name="quantity" />
                    </label>
                    {can('configure') && (
                      <>
                        <label>
                          Wymagane sesje
                          <input
                            name="required_sessions"
                            type="number"
                            min={1}
                            max={100}
                            defaultValue={1}
                          />
                        </label>
                        <label>
                          Badania dodatkowe (klucze po przecinku)
                          <input name="extra" />
                        </label>
                      </>
                    )}
                    <button>Dodaj zlecenie</button>
                  </form>
                </details>
              )}
              <section className="panel">
                <div className="panelbar">
                  <h2>
                    Kolejka badań <small>{filteredOrders.length} zleceń</small>
                  </h2>
                  <input
                    aria-label="Szukaj lotto"
                    placeholder="Szukaj lotto lub artykułu…"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                  />
                </div>
                <div className="tablewrap">
                  <table>
                    <thead>
                      <tr>
                        {['Lotto / bela', 'Artykuł', 'Zgłoszono', 'Status partii', 'Działanie'].map(
                          (x) => (
                            <th key={x}>{x}</th>
                          ),
                        )}
                      </tr>
                    </thead>
                    <tbody>
                      {filteredOrders.map((o) => (
                        <tr key={o.id}>
                          <td>
                            <strong>{o.lot}</strong>
                            <small>
                              Bela {o.roll || 'brak'} · {o.required_sessions} sesji
                            </small>
                          </td>
                          <td>
                            <strong>{o.code}</strong>
                            <small>{o.article}</small>
                          </td>
                          <td>
                            {new Date(o.created).toLocaleDateString('pl-PL')}
                            <small>
                              {o.completed &&
                                `Zbadano ${new Date(o.completed).toLocaleDateString('pl-PL')}`}
                            </small>
                          </td>
                          <td>
                            <span className={'badge ' + o.status}>{statuses[o.status]}</span>
                            {o.history.length > 0 && (
                              <details>
                                <summary>Historia dyspozycji</summary>
                                {o.history.map((h, i) => (
                                  <p key={i}>
                                    {h.held ? 'Wstrzymano' : 'Cofnięto wstrzymanie'}: {h.reason}
                                    <small>
                                      {h.author} · {new Date(h.date).toLocaleString('pl-PL')}
                                    </small>
                                  </p>
                                ))}
                              </details>
                            )}
                          </td>
                          <td>
                            {can('test') && ['WAITING', 'IN_PROGRESS'].includes(o.status) && (
                              <button
                                className="secondary"
                                onClick={() => void run(() => begin(o))}
                              >
                                Wykonaj badanie →
                              </button>
                            )}
                            {can('hold') && ['TESTED', 'HELD'].includes(o.status) && (
                              <button
                                className="text"
                                onClick={() => void run(() => changeDisposition(o))}
                              >
                                {o.status === 'HELD' ? 'Cofnij wstrzymanie' : 'Wstrzymaj'}
                              </button>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {!filteredOrders.length && (
                    <div className="empty">
                      Brak zleceń w tym widoku. Dodaj nowe lotto lub zmień filtr.
                    </div>
                  )}
                </div>
                <footer>
                  Zbadanie partii nie stanowi formalnej decyzji o zwolnieniu do produkcji lub
                  wysyłki.
                </footer>
              </section>
            </>
          )}
          {page === 'test' &&
            (!plan ? (
              <section className="panel empty">
                <h2>Wybierz lotto z kolejki</h2>
                <p>Zakres badań i cykl wynikają z konfiguracji artykułu.</p>
                <button onClick={() => setPage('orders')}>Przejdź do zleceń</button>
              </section>
            ) : (
              <form onSubmit={save}>
                <section className="panel">
                  <div className="panelbar">
                    <h2>
                      {plan.code} · {plan.article}
                    </h2>
                    <span className="badge IN_PROGRESS">
                      Cykl {plan.cycle} · Wersja {plan.version}
                    </span>
                  </div>
                  <div className="inlineform">
                    <label>
                      Lotto
                      <input value={selectedOrder!.lot} readOnly />
                    </label>
                    <label>
                      Bela
                      <input value={selectedOrder!.roll} readOnly />
                    </label>
                    <label>
                      Data badania
                      <input type="date" name="test_date" required defaultValue={localDate()} />
                    </label>
                    <label>
                      Operator
                      <input value={user.login} readOnly />
                    </label>
                    <label>
                      Numer WZ
                      <input name="delivery_note" />
                    </label>
                    <label>
                      Poziom produkcji
                      <input name="production_level" />
                    </label>
                    <label>
                      Urządzenie
                      <input name="device" maxLength={250} />
                    </label>
                    <label>
                      Rozpoczęcie badania
                      <input name="started_on" type="date" />
                    </label>
                    <label>
                      Zakończenie badania
                      <input name="ended_on" type="date" />
                    </label>
                  </div>
                </section>
                <div className="panel">
                  <div className="panelbar">
                    <h2>{correction ? `Korekta sesji #${correction.id}` : 'Wyniki pomiarów'}</h2>
                    <small>Niebieskie pola: pomiary · Białe pola: konfiguracja</small>
                  </div>
                  {plan.specs.map((s) => {
                    const v = values[s.key] || [],
                      filled = v.length === s.count && v.every((x) => x !== ''),
                      avg =
                        s.kind === 'numeric' && filled
                          ? v.reduce((a, b) => a + Number(b.replace(',', '.')), 0) / s.count
                          : null,
                      ok =
                        filled &&
                        (s.kind === 'numeric'
                          ? inSpec(avg!, s)
                          : v.every((x) => s.passing.includes(x)));
                    return (
                      <div className="measurement" key={s.key}>
                        <div className="spec">
                          <strong>{s.name}</strong>
                          <small>
                            {s.method} · {tolerance(s)}
                          </small>
                          <small>
                            {s.frequency === 'nth'
                              ? `Co ${s.every_n}. badanie`
                              : 'Badanie wymagane'}
                          </small>
                        </div>
                        <div className="points">
                          {s.labels.map((label, i) => {
                            const bad =
                              v[i] !== '' &&
                              (s.kind === 'numeric'
                                ? !inSpec(Number(v[i]?.replace(',', '.')), s)
                                : !s.passing.includes(v[i]));
                            return (
                              <label key={i}>
                                {label}
                                {s.kind === 'numeric' ? (
                                  <input
                                    aria-label={`${s.name} ${label}`}
                                    className={'resultinput ' + (bad ? 'outside' : '')}
                                    inputMode="decimal"
                                    required
                                    value={v[i] || ''}
                                    onChange={(e) => {
                                      const vv = [...v];
                                      vv[i] = e.target.value;
                                      setValues({ ...values, [s.key]: vv });
                                      setAck(false);
                                    }}
                                  />
                                ) : (
                                  <select
                                    aria-label={`${s.name} ${label}`}
                                    className={'resultinput ' + (bad ? 'outside' : '')}
                                    required
                                    value={v[i] || ''}
                                    onChange={(e) => {
                                      const vv = [...v];
                                      vv[i] = e.target.value;
                                      setValues({ ...values, [s.key]: vv });
                                      setAck(false);
                                    }}
                                  >
                                    <option value="">Wybierz</option>
                                    {s.allowed.map((x) => (
                                      <option key={x}>{x}</option>
                                    ))}
                                  </select>
                                )}
                              </label>
                            );
                          })}
                        </div>
                        <div className={'average ' + (filled && !ok ? 'outside' : '')}>
                          <small>{s.kind === 'numeric' ? 'Średnia' : 'Ocena'}</small>
                          <strong>
                            {filled
                              ? s.kind === 'numeric'
                                ? fmt(String(avg), s.decimals)
                                : ok
                                  ? 'OK'
                                  : 'NOK'
                              : 'Brak wyników'}
                          </strong>
                          {filled && (
                            <span className={'badge ' + (ok ? 'TESTED' : 'HELD')}>
                              {ok ? 'OK' : 'NOK'}
                            </span>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
                <section className="panel inlineform">
                  <label>
                    Uwagi
                    <textarea name="notes" maxLength={4000} />
                  </label>
                  {warning && (
                    <label className="warning">
                      <input
                        type="checkbox"
                        checked={ack}
                        onChange={(e) => setAck(e.target.checked)}
                      />{' '}
                      Potwierdzam ostrzeżenia o wynikach poza tolerancją. Zapisuję rzeczywiste
                      wyniki.
                    </label>
                  )}
                  <div>
                    <button disabled={!complete(plan.specs, values) || (warning && !ack) || saving}>
                      {saving ? 'Zapisywanie…' : 'Zatwierdź i zapisz badanie'}
                    </button>
                    <small>
                      Wszystkie wymagane pola muszą być kompletne. Backend ustala ostateczną ocenę.
                    </small>
                  </div>
                </section>
              </form>
            ))}
          {['real', 'simulated', 'recover'].includes(page) && (
            <>
              <div
                className={
                  page === 'simulated' || (page === 'recover' && source === 'simulated')
                    ? 'simulation'
                    : 'modulehint'
                }
              >
                {page === 'simulated' || (page === 'recover' && source === 'simulated')
                  ? 'SIMULATED DATA · Dane nie służą do oceny ani zwalniania partii.'
                  : 'Wyniki rzeczywiste · Każdy wiersz odpowiada osobnej sesji badawczej.'}
              </div>
              <section className="panel">
                <form
                  className="inlineform"
                  onSubmit={(e) => {
                    e.preventDefault();
                    void run(() => loadResults());
                  }}
                >
                  {page === 'recover' && (
                    <label>
                      Źródło
                      <select
                        value={source}
                        onChange={(e) => {
                          setSource(e.target.value);
                          setRecords([]);
                          setScope(e.target.value);
                        }}
                      >
                        {can('real') && <option value="real">Wyniki rzeczywiste</option>}
                        {can('simulated') && <option value="simulated">Wyniki symulowane</option>}
                      </select>
                    </label>
                  )}
                  <label>
                    Numer lotto
                    <input
                      value={search}
                      onChange={(e) => setSearch(e.target.value)}
                      placeholder="Szukaj lotto…"
                    />
                  </label>
                  <label>
                    Artykuł
                    <select
                      value={articleFilter}
                      onChange={(e) => setArticleFilter(e.target.value)}
                    >
                      <option value="">Wszystkie</option>
                      {articles.map((a) => (
                        <option key={a.id} value={a.id}>
                          {a.code}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Data od
                    <input type="date" value={start} onChange={(e) => setStart(e.target.value)} />
                  </label>
                  <label>
                    Data do
                    <input type="date" value={end} onChange={(e) => setEnd(e.target.value)} />
                  </label>
                  <button>Wyszukaj</button>
                  <button
                    type="button"
                    className="secondary"
                    onClick={() => setScope(page === 'recover' ? source : page)}
                  >
                    Potwierdź hasło
                  </button>
                </form>
                <div className="panelbar">
                  <small>Do 100 sesji na stronę. Kolumny zachowują wersję tolerancji.</small>
                  <a
                    className="button secondary"
                    href={`/api/export/${page === 'recover' ? source : page}?${new URLSearchParams({ lot: search, ...(articleFilter ? { article_id: articleFilter } : {}), ...(start ? { start } : {}), ...(end ? { end } : {}) })}`}
                  >
                    Eksport XLSX ↓
                  </a>
                </div>
                <Results
                  records={sort ? [...records].reverse() : records}
                  select={setDetail}
                  sort={() => setSort(!sort)}
                />
                <div className="panelbar">
                  <button
                    className="secondary"
                    disabled={records.length < 100}
                    onClick={() =>
                      void run(async () => {
                        const src = page === 'recover' ? source : page;
                        const q = new URLSearchParams({
                          lot: search,
                          offset: String(records.length),
                          ...(articleFilter ? { article_id: articleFilter } : {}),
                          ...(start ? { start } : {}),
                          ...(end ? { end } : {}),
                        });
                        setRecords([
                          ...records,
                          ...(await api<LabResult[]>(`/results/${src}?${q}`)),
                        ]);
                      })
                    }
                  >
                    Załaduj kolejne
                  </button>
                  <small>Wyświetlono {records.length} sesji</small>
                </div>
              </section>
              {page === 'recover' && source === 'real' && (
                <section className="panel">
                  <div className="panelbar">
                    <h2>Historia z Excela do weryfikacji</h2>
                    <button
                      className="secondary"
                      onClick={() =>
                        void run(async () =>
                          setHistory(
                            await api<any[]>('/history?lot=' + encodeURIComponent(search)),
                          ),
                        )
                      }
                    >
                      Szukaj w historii
                    </button>
                  </div>
                  {history.map((h) => (
                    <details key={h.id}>
                      <summary>
                        {h.lot} · wiersz {h.row} · {h.label}
                      </summary>
                      <p>{h.issues.join('; ')}</p>
                      <div className="tablewrap">
                        <table>
                          <tbody>
                            {Object.entries(h.values).map(([k, v]) => (
                              <tr key={k}>
                                <th>{k}</th>
                                <td>{String(v)}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </details>
                  ))}
                </section>
              )}
            </>
          )}
          {page === 'articles' && (
            <>
              <section className="panel">
                <div className="panelbar">
                  <h2>Katalog artykułów</h2>
                  <button
                    className="secondary"
                    onClick={() => setDraft({ code: '', name: '', specs: [] })}
                  >
                    Nowy artykuł
                  </button>
                </div>
                <div className="cards">
                  {articles.map((a) => (
                    <div key={a.id}>
                      <strong>{a.code}</strong>
                      <p>{a.name}</p>
                      <small>{a.cycle} zapisanych cykli</small>
                      <button
                        className="text"
                        onClick={() => void run(() => loadDraft(String(a.id)))}
                      >
                        Edytuj konfigurację
                      </button>
                      <button
                        className="text"
                        onClick={() => void run(() => loadDraft(String(a.id), true))}
                      >
                        Kopiuj do nowego
                      </button>
                    </div>
                  ))}
                </div>
              </section>
              <form
                className="panel"
                onSubmit={(e) => {
                  e.preventDefault();
                  void run(async () => {
                    await api(
                      draft.id ? `/articles/${draft.id}/config` : '/articles',
                      'POST',
                      draft,
                    );
                    setNotice('Zapisano nową wersję konfiguracji. Historia pozostaje bez zmian.');
                    await refresh();
                  });
                }}
              >
                <div className="panelbar">
                  <h2>{draft.id ? 'Nowa wersja konfiguracji' : 'Definicja artykułu'}</h2>
                </div>
                <div className="inlineform">
                  <label>
                    Kod artykułu
                    <input
                      required
                      value={draft.code}
                      readOnly={!!draft.id}
                      onChange={(e) => setDraft({ ...draft, code: e.target.value })}
                    />
                  </label>
                  <label>
                    Nazwa artykułu
                    <input
                      required
                      value={draft.name}
                      readOnly={!!draft.id}
                      onChange={(e) => setDraft({ ...draft, name: e.target.value })}
                    />
                  </label>
                </div>
                {draft.specs.map((s, i) => (
                  <fieldset key={i}>
                    <legend>
                      {i + 1}. {s.name || 'Nowa charakterystyka'}
                    </legend>
                    <div className="inlineform">
                      <label>
                        Klucz
                        <input
                          required
                          value={s.key}
                          onChange={(e) => patchSpec(i, { key: e.target.value })}
                        />
                      </label>
                      <label>
                        Nazwa
                        <input
                          required
                          value={s.name}
                          onChange={(e) => patchSpec(i, { name: e.target.value })}
                        />
                      </label>
                      <label>
                        Norma
                        <select
                          required
                          value={s.method_id || ''}
                          onChange={(e) => patchSpec(i, { method_id: Number(e.target.value) })}
                        >
                          <option value="">Wybierz normę</option>
                          {methods.map((m) => (
                            <option key={m.id} value={m.id}>
                              {m.code}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label>
                        Jednostka
                        <input
                          value={s.unit}
                          onChange={(e) => patchSpec(i, { unit: e.target.value })}
                        />
                      </label>
                      <label>
                        Typ wyniku
                        <select
                          value={s.kind}
                          onChange={(e) => patchSpec(i, { kind: e.target.value as Spec['kind'] })}
                        >
                          <option value="numeric">Liczbowy</option>
                          <option value="qualitative">Jakościowy</option>
                        </select>
                      </label>
                      <label>
                        Liczba pomiarów
                        <input
                          type="number"
                          min={1}
                          max={10}
                          value={s.count}
                          onChange={(e) => {
                            const n = Math.min(10, Math.max(1, Number(e.target.value)));
                            patchSpec(i, {
                              count: n,
                              labels: Array.from(
                                { length: n },
                                (_, j) => s.labels[j] || `Pomiar ${j + 1}`,
                              ),
                            });
                          }}
                        />
                      </label>
                      <label>
                        Punkty (oddzielone przecinkami)
                        <input
                          required
                          value={s.labels.join(',')}
                          onChange={(e) => patchSpec(i, { labels: e.target.value.split(',') })}
                        />
                      </label>
                      <label>
                        Częstotliwość
                        <select
                          value={s.frequency}
                          onChange={(e) =>
                            patchSpec(i, { frequency: e.target.value as Spec['frequency'] })
                          }
                        >
                          <option value="every">Każde badanie</option>
                          <option value="nth">Co N-te badanie</option>
                          <option value="extra">Dodatkowe</option>
                        </select>
                      </label>
                      {s.frequency === 'nth' && (
                        <label>
                          Co ile sesji
                          <input
                            type="number"
                            min={1}
                            value={s.every_n}
                            onChange={(e) => patchSpec(i, { every_n: Number(e.target.value) })}
                          />
                        </label>
                      )}
                      {s.kind === 'numeric' ? (
                        <>
                          <label>
                            LSL
                            <input
                              value={s.lsl ?? ''}
                              onChange={(e) => patchSpec(i, { lsl: e.target.value || null })}
                            />
                          </label>
                          <label>
                            Operator LSL
                            <select
                              value={String(s.lower_inclusive)}
                              onChange={(e) =>
                                patchSpec(i, { lower_inclusive: e.target.value === 'true' })
                              }
                            >
                              <option value="true">≥</option>
                              <option value="false">&gt;</option>
                            </select>
                          </label>
                          <label>
                            USL
                            <input
                              value={s.usl ?? ''}
                              onChange={(e) => patchSpec(i, { usl: e.target.value || null })}
                            />
                          </label>
                          <label>
                            Operator USL
                            <select
                              value={String(s.upper_inclusive)}
                              onChange={(e) =>
                                patchSpec(i, { upper_inclusive: e.target.value === 'true' })
                              }
                            >
                              <option value="true">≤</option>
                              <option value="false">&lt;</option>
                            </select>
                          </label>
                          <label>
                            Miejsca dziesiętne
                            <input
                              type="number"
                              min={0}
                              max={10}
                              value={s.decimals}
                              onChange={(e) => patchSpec(i, { decimals: Number(e.target.value) })}
                            />
                          </label>
                          <label>
                            Korekta jednostronna (opcjonalnie)
                            <input
                              value={s.simulation_offset ?? ''}
                              onChange={(e) =>
                                patchSpec(i, { simulation_offset: e.target.value || null })
                              }
                            />
                          </label>
                        </>
                      ) : (
                        <>
                          <label>
                            Dopuszczalne wyniki (przecinki)
                            <input
                              value={s.allowed.join(',')}
                              onChange={(e) => patchSpec(i, { allowed: e.target.value.split(',') })}
                            />
                          </label>
                          <label>
                            Wyniki zgodne (przecinki)
                            <input
                              value={s.passing.join(',')}
                              onChange={(e) => patchSpec(i, { passing: e.target.value.split(',') })}
                            />
                          </label>
                        </>
                      )}
                      <button
                        className="text"
                        type="button"
                        onClick={() =>
                          setDraft({ ...draft, specs: draft.specs.filter((_, j) => j !== i) })
                        }
                      >
                        Usuń z nowej wersji
                      </button>
                      {i > 0 && (
                        <button
                          type="button"
                          className="text"
                          onClick={() => {
                            const arr = [...draft.specs];
                            [arr[i - 1], arr[i]] = [arr[i], arr[i - 1]];
                            setDraft({ ...draft, specs: arr });
                          }}
                        >
                          Przesuń wyżej
                        </button>
                      )}
                    </div>
                  </fieldset>
                ))}
                <div className="inlineform">
                  <button
                    type="button"
                    className="secondary"
                    onClick={() => setDraft({ ...draft, specs: [...draft.specs, blankSpec()] })}
                  >
                    ＋ Dodaj charakterystykę
                  </button>
                  <button disabled={!draft.specs.length}>Zapisz wersję konfiguracji</button>
                </div>
              </form>
              <section className="panel">
                <h2>Centralny katalog metod</h2>
                <div className="chips">
                  {methods.map((m) => (
                    <span key={m.id}>
                      {m.code} · {m.name}
                    </span>
                  ))}
                </div>
                <form
                  className="inlineform"
                  onSubmit={(e) => {
                    e.preventDefault();
                    const f = e.currentTarget;
                    void run(async () => {
                      await api('/methods', 'POST', Object.fromEntries(new FormData(f)));
                      f.reset();
                      await refresh();
                    });
                  }}
                >
                  <label>
                    Kod normy
                    <input name="code" required />
                  </label>
                  <label>
                    Nazwa metody
                    <input name="name" required />
                  </label>
                  <button>Dodaj metodę</button>
                </form>
              </section>
            </>
          )}
          {page === 'spc' && (
            <section className="panel">
              <div className="inlineform">
                <label>
                  Zatwierdzona konfiguracja
                  <select value={chartId} onChange={(e) => setChartId(e.target.value)}>
                    <option value="">Wybierz kartę</option>
                    {spcConfigs.map((c) => (
                      <option key={c.id} value={c.id}>
                        #{c.id} · {c.name} · n={c.limits.n}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Data od
                  <input type="date" value={start} onChange={(e) => setStart(e.target.value)} />
                </label>
                <label>
                  Data do
                  <input type="date" value={end} onChange={(e) => setEnd(e.target.value)} />
                </label>
                <button
                  disabled={!chartId}
                  onClick={() =>
                    void run(async () =>
                      setChart(
                        await api(
                          `/spc/chart/${chartId}?${new URLSearchParams({ ...(start ? { start } : {}), ...(end ? { end } : {}) })}`,
                        ),
                      ),
                    )
                  }
                >
                  Pokaż kartę
                </button>
                <button className="secondary" onClick={() => setScope('spc')}>
                  Potwierdź hasło
                </button>
              </div>
              {chart ? (
                <>
                  <div className="modulehint">Plan próbkowania: {chart.sampling_plan}</div>
                  <SpcChart data={chart} />
                  <div className="inlineform">
                    <a
                      className="button secondary"
                      href={`/api/spc/export/${chartId}?${new URLSearchParams({ ...(start ? { start } : {}), ...(end ? { end } : {}) })}`}
                    >
                      Eksport SPC XLSX
                    </a>
                    <button className="secondary" onClick={() => window.print()}>
                      Drukuj / zapisz PDF
                    </button>
                  </div>
                  <p>
                    Alarmy ostatniego punktu:{' '}
                    {chart.alarms.length ? chart.alarms.map((a: any) => a.type).join(', ') : 'brak'}
                  </p>
                </>
              ) : (
                <div className="empty">
                  Wybierz zatwierdzony plan SPC. Granice kontrolne są niezależne od tolerancji
                  wyrobu.
                </div>
              )}
            </section>
          )}
          {page === 'admin' && (
            <Admin
              methods={methods}
              specs={allSpecs}
              rules={notifications}
              users={users}
              audit={audit}
              canUsers={!!can('users')}
              run={run}
              reload={adminLoad}
              requireSpc={() => setScope('spc')}
            />
          )}
        </main>
      </section>
      {scope && (
        <div className="overlay">
          <form
            className="dialog"
            onSubmit={(e) => {
              e.preventDefault();
              void run(authorize);
            }}
          >
            <p className="eyebrow">CHRONIONY MODUŁ</p>
            <h2>Potwierdź dostęp</h2>
            <p>
              {scope === 'spc'
                ? 'Analiza SPC'
                : scope === 'real'
                  ? 'Wyniki rzeczywiste'
                  : 'Wyniki symulowane'}
              . Autoryzacja wygasa po 15 minutach.
            </p>
            <label>
              Twoje hasło
              <input
                type="password"
                autoFocus
                autoComplete="current-password"
                value={reauthPw}
                onChange={(e) => setReauthPw(e.target.value)}
                required
              />
            </label>
            <div className="inlineform">
              <button>Odblokuj moduł</button>
              <button
                type="button"
                className="secondary"
                onClick={() => {
                  setScope(null);
                  setReauthPw('');
                }}
              >
                Anuluj
              </button>
            </div>
            {error && <p className="error">{error}</p>}
          </form>
        </div>
      )}
      {detail && (
        <div className="overlay">
          <div className="dialog wide">
            <div className="panelbar">
              <h2>
                Sesja #{detail.id} · {detail.lot}
              </h2>
              <button className="secondary" onClick={() => setDetail(null)}>
                Zamknij
              </button>
            </div>
            <p className={detail.source === 'simulated' ? 'simulation' : 'modulehint'}>
              {detail.label}
            </p>
            <p>
              {detail.code} · {detail.article} · Bela {detail.roll} · Cykl {detail.cycle} ·{' '}
              {detail.test_date} · {detail.operator}
            </p>
            <p>
              WZ: {detail.metadata.delivery_note} · Poziom: {detail.metadata.production_level} ·
              Urządzenie: {detail.metadata.device} · Od {detail.metadata.started_on} do{' '}
              {detail.metadata.ended_on} · Uwagi: {detail.metadata.notes}
            </p>
            <div className="tablewrap">
              <table>
                <thead>
                  <tr>
                    <th>Charakterystyka</th>
                    <th>Norma i tolerancja</th>
                    <th>Pomiary</th>
                    <th>Średnia</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {detail.results.map((r) => (
                    <tr key={r.spec.key}>
                      <td>{r.spec.name}</td>
                      <td>
                        {r.spec.method}
                        <small>{tolerance(r.spec)}</small>
                      </td>
                      <td>
                        {r.values.map((v, i) => (
                          <span
                            key={i}
                            className={'value ' + (!r.individual_ok[i] ? 'outside' : '')}
                          >
                            {r.spec.labels[i]}:{' '}
                            {r.spec.kind === 'numeric' ? fmt(v, r.spec.decimals) : v}
                            {r.transforms[i] && <small>{r.transforms[i].parameters.outcome}</small>}
                          </span>
                        ))}
                      </td>
                      <td className={r.ok ? '' : 'outside'}>
                        {r.average === null ? 'Brak średniej' : fmt(r.average, r.spec.decimals)}
                      </td>
                      <td>{r.ok ? 'OK' : 'NOK'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {detail.correction_of && (
              <p>
                Korekta sesji #{detail.correction_of}: {detail.reason}
              </p>
            )}
            <a className="button" href={`/api/export/${detail.source}?session_id=${detail.id}`}>
              Eksport formularza XLSX
            </a>
            {detail.source === 'real' && can('configure') && (
              <button
                className="secondary"
                onClick={() => {
                  const reason = window.prompt(
                    'Uzasadnienie korekty. Poprzednie wyniki zostaną zachowane.',
                  );
                  if (!reason || reason.trim().length < 3) return;
                  const o = orders.find((x) => x.id === detail.order_id);
                  if (!o) {
                    setError('Odśwież listę zleceń.');
                    return;
                  }
                  setCorrection({ id: detail.id, reason });
                  setSelectedOrder(o);
                  setPlan({
                    article: detail.article,
                    code: detail.code,
                    cycle: detail.cycle,
                    config_id: detail.config_id,
                    version: detail.revision + 1,
                    specs: detail.results.map((r) => r.spec),
                  });
                  setValues(Object.fromEntries(detail.results.map((r) => [r.spec.key, r.values])));
                  setAck(false);
                  setDetail(null);
                  setPage('test');
                }}
              >
                Utwórz korektę
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

/** Dynamiczna tabela grupuje kolumny według charakterystyki i wersji konfiguracji. */
function Results({
  records,
  select,
  sort,
}: {
  records: LabResult[];
  select: (r: LabResult) => void;
  sort: () => void;
}) {
  const cols = new Map<string, Spec>();
  records.forEach((d) =>
    d.results.forEach((r) => cols.set(`${d.config_id}:${r.spec.key}`, r.spec)),
  );
  return (
    <div className="tablewrap">
      <table>
        <thead>
          <tr>
            <th>Lotto / formularz</th>
            <th>Artykuł</th>
            <th>
              <button className="text" onClick={sort}>
                Cykl ↕
              </button>
            </th>
            <th>Data / operator</th>
            {[...cols].map(([key, s]) => (
              <th key={key}>
                {s.name}
                <small>
                  {s.method} · {tolerance(s)} · cfg {key.split(':')[0]}
                </small>
              </th>
            ))}
            <th>Status sesji</th>
          </tr>
        </thead>
        <tbody>
          {records.map((d) => (
            <tr key={d.id}>
              <td>
                <button className="text" onClick={() => select(d)}>
                  {d.lot} ↗
                </button>
                <small>
                  Bela {d.roll || 'brak'} · Sesja #{d.id}
                </small>
              </td>
              <td>{d.code}</td>
              <td>{d.cycle}</td>
              <td>
                {d.test_date}
                <small>{d.operator}</small>
              </td>
              {[...cols].map(([key, s]) => {
                const r = d.results.find((x) => `${d.config_id}:${x.spec.key}` === key);
                return (
                  <td key={key}>
                    {r ? (
                      <>
                        <div className="nowrap">
                          {r.values.map((v, i) => (
                            <span
                              key={i}
                              className={'value ' + (!r.individual_ok[i] ? 'outside' : '')}
                            >
                              {s.kind === 'numeric' ? fmt(v, s.decimals) : v}
                            </span>
                          ))}
                        </div>
                        {r.average !== null && (
                          <div className={'meanvalue ' + (!r.ok ? 'outside' : '')}>
                            Śr. {fmt(r.average, s.decimals)}
                          </div>
                        )}
                      </>
                    ) : (
                      'Nie wymagano'
                    )}
                  </td>
                );
              })}
              <td>
                <span className={'badge ' + (d.ok ? 'TESTED' : 'HELD')}>{d.ok ? 'OK' : 'NOK'}</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {records.length === 0 && (
        <div className="empty">Brak wyników. Potwierdź hasło i wybierz zakres wyszukiwania.</div>
      )}
    </div>
  );
}

/** Rysuje dwie zsynchronizowane karty wraz z liniami kontrolnymi i specyfikacją. */
function SpcChart({ data }: { data: any }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    const c = echarts.init(ref.current),
      l = data.limits;
    const lines = (keys: string[]) =>
      keys.map((k) => ({
        name: k.toUpperCase(),
        yAxis: l[k],
        lineStyle: { type: 'dashed' as const, color: k.includes('cl') ? '#b6515e' : '#368277' },
        label: { formatter: k.toUpperCase() },
      }));
    c.setOption({
      animation: false,
      color: ['#147b84', '#557dbe'],
      tooltip: { trigger: 'axis' },
      legend: { data: ['Średnia', 'Rozstęp'] },
      grid: [
        { left: 70, right: 60, top: 50, height: '32%' },
        { left: 70, right: 60, top: '58%', height: '27%' },
      ],
      xAxis: [0, 1].map((i) => ({
        type: 'category',
        gridIndex: i,
        data: data.labels.map((x: any) => `${x.date} / ${x.lot}`),
        axisLabel: { rotate: 20 },
      })),
      yAxis: [
        { type: 'value', scale: true, gridIndex: 0, name: data.spec.unit },
        { type: 'value', scale: true, gridIndex: 1, name: l.n === 1 ? 'MR' : 'R' },
      ],
      series: [
        {
          name: 'Średnia',
          type: 'line',
          data: data.means,
          xAxisIndex: 0,
          yAxisIndex: 0,
          markLine: {
            symbol: 'none',
            data: [
              ...lines(['cl', 'lcl', 'ucl']),
              ...['lsl', 'usl']
                .filter((k) => data.spec[k] !== null)
                .map((k) => ({
                  name: k.toUpperCase(),
                  yAxis: Number(data.spec[k]),
                  lineStyle: { color: '#d69a33' },
                  label: { formatter: k.toUpperCase() },
                })),
            ],
          },
        },
        {
          name: 'Rozstęp',
          type: 'line',
          data: data.ranges,
          xAxisIndex: 1,
          yAxisIndex: 1,
          markLine: { symbol: 'none', data: lines(['rcl', 'rlcl', 'rucl']) },
        },
      ],
    });
    const resize = () => c.resize();
    window.addEventListener('resize', resize);
    return () => {
      window.removeEventListener('resize', resize);
      c.dispose();
    };
  }, [data]);
  return <div ref={ref} className="chart" role="img" aria-label="Karta średnich i rozstępów SPC" />;
}

/** Panel zarządzania użytkownikami, alarmami, importem i zatwierdzaniem SPC. */
function Admin({
  specs,
  rules,
  users,
  audit,
  canUsers,
  run,
  reload,
  requireSpc,
}: {
  methods: Method[];
  specs: Spec[];
  rules: any;
  users: any[];
  audit: any[];
  canUsers: boolean;
  run: (fn: () => Promise<void>) => Promise<void>;
  reload: () => Promise<void>;
  requireSpc: () => void;
}) {
  const [tab, setTab] = useState('spc'),
    [msg, setMsg] = useState(''),
    [proposal, setProposal] = useState<any>(null),
    [editUser, setEditUser] = useState<any>(null);
  return (
    <section className="panel">
      <div className="tabs">
        {['spc', 'powiadomienia', 'import', 'użytkownicy', 'historia']
          .filter((t) => t !== 'użytkownicy' || canUsers)
          .map((t) => (
            <button key={t} className={tab === t ? '' : 'secondary'} onClick={() => setTab(t)}>
              {t}
            </button>
          ))}
      </div>
      {msg && <p className="success">{msg}</p>}
      {tab === 'spc' && (
        <>
          <h2>Zatwierdzenie planu SPC</h2>
          <p>
            Granice należy wyznaczyć z zatwierdzonej próby bazowej. LH/M/RH wymaga uzasadnienia jako
            podgrupa.
          </p>
          <button className="secondary" onClick={requireSpc}>
            Potwierdź hasło modułu SPC
          </button>
          <form
            className="inlineform"
            onSubmit={(e) => {
              e.preventDefault();
              const f = Object.fromEntries(new FormData(e.currentTarget));
              const payload: Record<string, unknown> = { ...f };
              for (const k of [
                'characteristic_id',
                'n',
                'cl',
                'lcl',
                'ucl',
                'rcl',
                'rlcl',
                'rucl',
                'run_length',
              ])
                payload[k] = Number(f[k]);
              void run(async () => {
                await api('/spc/configs', 'POST', payload);
                setMsg('Zatwierdzono nową konfigurację SPC.');
                await reload();
              });
            }}
          >
            <label>
              Charakterystyka
              <select name="characteristic_id" required>
                <option value="">Wybierz</option>
                {specs
                  .filter((s) => s.kind === 'numeric')
                  .map((s) => (
                    <option key={s.id} value={s.id}>
                      #{s.id} · {s.name} · n={s.count}
                    </option>
                  ))}
              </select>
            </label>
            <button
              type="button"
              className="secondary"
              onClick={(e) => {
                const form = e.currentTarget.closest('form')!;
                const data = new FormData(form);
                void run(async () => {
                  const p = await api<any>(
                    `/spc/proposal/${data.get('characteristic_id')}?${new URLSearchParams({ ...(data.get('baseline_start') ? { start: String(data.get('baseline_start')) } : {}), ...(data.get('baseline_end') ? { end: String(data.get('baseline_end')) } : {}) })}`,
                  );
                  setProposal(p.limits);
                  setMsg(`Propozycja z ${p.subgroups} podgrup. Wymaga przeglądu i zatwierdzenia.`);
                });
              }}
            >
              Wylicz propozycję granic
            </button>
            <label>
              Próba bazowa od
              <input type="date" name="baseline_start" />
            </label>
            <label>
              Próba bazowa do
              <input type="date" name="baseline_end" />
            </label>
            <label>
              Plan próbkowania
              <textarea name="sampling_plan" required minLength={10} />
            </label>
            {[
              ['n', 'Liczność podgrupy', 3],
              ['cl', 'CL średniej', 0],
              ['lcl', 'LCL średniej', 0],
              ['ucl', 'UCL średniej', 0],
              ['rcl', 'CL rozstępu', 0],
              ['rlcl', 'LCL rozstępu', 0],
              ['rucl', 'UCL rozstępu', 0],
              ['run_length', 'Długość serii (0 wyłącza)', 8],
            ].map(([k, label, v]) => (
              <label key={k}>
                {label}
                <input
                  key={String(k) + String(proposal?.[String(k)])}
                  name={String(k)}
                  type="number"
                  step="any"
                  required
                  defaultValue={proposal?.[String(k)] ?? v}
                />
              </label>
            ))}
            <button>Zatwierdź konfigurację</button>
          </form>
        </>
      )}
      {tab === 'powiadomienia' && (
        <>
          <h2>Powiadomienia jakościowe</h2>
          <p>
            SMTP jest konfigurowane w środowisku serwera. Dane symulowane nie uruchamiają alarmów.
          </p>
          <form
            className="inlineform"
            onSubmit={(e) => {
              e.preventDefault();
              const f = Object.fromEntries(new FormData(e.currentTarget));
              void run(async () => {
                await api('/notifications', 'POST', {
                  characteristic_id: Number(f.characteristic_id),
                  email: f.email,
                  events: [f.event],
                  enabled: f.enabled === 'on',
                });
                setMsg('Dodano regułę.');
                await reload();
              });
            }}
          >
            <label>
              Charakterystyka
              <select name="characteristic_id" required>
                {specs.map((s) => (
                  <option key={s.id} value={s.id}>
                    #{s.id} · {s.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              E-mail odbiorcy
              <input name="email" type="email" required />
            </label>
            <label>
              Zdarzenie
              <select name="event">
                {['UCL', 'LCL', 'R_UCL', 'R_LCL', 'SPECIFICATION', 'RUN'].map((e) => (
                  <option key={e}>{e}</option>
                ))}
              </select>
            </label>
            <label>
              <input type="checkbox" name="enabled" /> Włącz regułę
            </label>
            <button>Dodaj odbiorcę</button>
          </form>
          <table>
            <thead>
              <tr>
                <th>Odbiorca</th>
                <th>Charakterystyka</th>
                <th>Zdarzenia</th>
                <th>Aktywna</th>
              </tr>
            </thead>
            <tbody>
              {rules.rules.map((r: any) => (
                <tr key={r.id}>
                  <td>{r.email}</td>
                  <td>{r.characteristic_id}</td>
                  <td>{r.events.join(', ')}</td>
                  <td>
                    <button
                      className="secondary"
                      onClick={() =>
                        void run(async () => {
                          await api(`/notifications/${r.id}`, 'PUT', { ...r, enabled: !r.enabled });
                          await reload();
                        })
                      }
                    >
                      {r.enabled ? 'Wyłącz' : 'Włącz'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <h2>Historia kolejki SMTP</h2>
          <div className="tablewrap">
            <table>
              <thead>
                <tr>
                  <th>Alarm</th>
                  <th>Odbiorca</th>
                  <th>Status SMTP</th>
                  <th>Data / błąd</th>
                </tr>
              </thead>
              <tbody>
                {rules.outbox.map((x: any) => (
                  <tr key={x.id}>
                    <td>{x.alert_id}</td>
                    <td>{x.recipient}</td>
                    <td>{x.status}</td>
                    <td>{x.sent_at || x.error || 'Oczekuje'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
      {tab === 'import' && (
        <>
          <h2>Import historii XLSM / XLSX</h2>
          <p>
            Import zachowuje wiersze źródłowe i zgłasza braki. Nie zatwierdza historycznych ocen ani
            nie wysyła powiadomień.
          </p>
          <form
            className="inlineform"
            onSubmit={(e) => {
              e.preventDefault();
              const f = new FormData(e.currentTarget);
              void run(async () => {
                const result = await api<any>('/import/history', 'POST', f);
                setMsg(
                  `Zaimportowano ${result.inserted} wierszy, pominięto ${result.skipped} duplikatów.`,
                );
              });
            }}
          >
            <label>
              Skoroszyt
              <input type="file" name="file" accept=".xlsm,.xlsx" required />
            </label>
            <button>Importuj do historii</button>
          </form>
        </>
      )}
      {tab === 'użytkownicy' && (
        <>
          <h2>Użytkownicy i role</h2>
          <form
            className="inlineform"
            onSubmit={(e) => {
              e.preventDefault();
              const f = e.currentTarget;
              void run(async () => {
                await api('/users', 'POST', Object.fromEntries(new FormData(f)));
                f.reset();
                setMsg('Utworzono użytkownika.');
                await reload();
              });
            }}
          >
            <label>
              Login
              <input name="login" required autoComplete="off" />
            </label>
            <label>
              Hasło
              <input
                name="password"
                type="password"
                minLength={12}
                required
                autoComplete="new-password"
              />
            </label>
            <label>
              Rola
              <select name="role">
                {['admin', 'manager', 'technician', 'reporter', 'reader'].map((r) => (
                  <option key={r}>{r}</option>
                ))}
              </select>
            </label>
            <button>Utwórz konto</button>
          </form>
          <table>
            <thead>
              <tr>
                <th>Login</th>
                <th>Rola</th>
                <th>Aktywny</th>
                <th>Zarządzaj</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td>{u.login}</td>
                  <td>{u.role}</td>
                  <td>{u.active ? 'Tak' : 'Nie'}</td>
                  <td>
                    <button className="secondary" onClick={() => setEditUser(u)}>
                      Edytuj konto
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {editUser && (
            <form
              className="inlineform"
              onSubmit={(e) => {
                e.preventDefault();
                const form = e.currentTarget;
                const f = Object.fromEntries(new FormData(form));
                void run(async () => {
                  await api(`/users/${editUser.id}`, 'PATCH', {
                    role: f.role,
                    active: f.active === 'on',
                    ...(f.password ? { password: f.password } : {}),
                  });
                  setEditUser(null);
                  setMsg('Zmieniono konto i unieważniono jego dotychczasowe sesje.');
                  await reload();
                });
              }}
            >
              <strong>{editUser.login}</strong>
              <label>
                Rola
                <select name="role" defaultValue={editUser.role}>
                  {['admin', 'manager', 'technician', 'reporter', 'reader'].map((r) => (
                    <option key={r}>{r}</option>
                  ))}
                </select>
              </label>
              <label>
                <input type="checkbox" name="active" defaultChecked={editUser.active} /> Konto
                aktywne
              </label>
              <label>
                Nowe hasło (opcjonalnie)
                <input name="password" type="password" minLength={12} autoComplete="new-password" />
              </label>
              <button>Zapisz zmiany konta</button>
              <button type="button" className="secondary" onClick={() => setEditUser(null)}>
                Anuluj
              </button>
            </form>
          )}
        </>
      )}
      {tab === 'historia' && (
        <>
          <h2>Rejestr zmian</h2>
          <div className="tablewrap">
            <table>
              <thead>
                <tr>
                  <th>Data</th>
                  <th>Autor ID</th>
                  <th>Operacja</th>
                  <th>Obiekt</th>
                  <th>Szczegóły</th>
                </tr>
              </thead>
              <tbody>
                {audit.map((a) => (
                  <tr key={a.id}>
                    <td>{new Date(a.created).toLocaleString('pl-PL')}</td>
                    <td>{a.author}</td>
                    <td>{a.action}</td>
                    <td>{a.entity}</td>
                    <td>
                      <details>
                        <summary>Pokaż</summary>
                        <pre>{JSON.stringify(a.payload, null, 2)}</pre>
                      </details>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  );
}
createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
