/** Dobiera stałą ikonę modułu, niezależnie od uprawnień i liczby pozycji menu. */
export function IkonaNawigacji({ modul }: { modul: string }) {
  if (modul === 'orders') {
    return (
      <svg viewBox="0 0 32 32" fill="currentColor" aria-hidden="true" focusable="false">
        <circle cx="5" cy="7" r="2.5" />
        <circle cx="5" cy="16" r="2.5" />
        <circle cx="5" cy="25" r="2.5" />
        <rect x="12" y="5" width="18" height="4" rx="2" />
        <rect x="12" y="14" width="18" height="4" rx="2" />
        <rect x="12" y="23" width="18" height="4" rx="2" />
      </svg>
    );
  }
  if (modul === 'admin') {
    return (
      <svg
        viewBox="0 0 40 40"
        fill="none"
        stroke="currentColor"
        strokeWidth="3"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
        focusable="false"
      >
        <circle cx="14" cy="11" r="7" />
        <path d="M18 36H4v-7a11 11 0 0 1 17-9" />
        <circle cx="25" cy="30" r="6" />
        <path d="m29 26 8-8m-4 4 3 3m-2-5 3 3" />
      </svg>
    );
  }
  const sciezki: Record<string, string> = {
    test: 'M9 3h6M10 3v6L4 19a1.5 1.5 0 0 0 1.3 2h13.4a1.5 1.5 0 0 0 1.3-2L14 9V3M7 15h10',
    real: 'M5 3h14v18H5zM8 8h8M8 12h8M8 16h5',
    simulated: 'm12 3 9 5-9 5-9-5 9-5M3 12l9 5 9-5M3 16l9 5 9-5',
    recover: 'M3 10a9 9 0 1 1 1 8M3 4v6h6M12 7v5l3 2',
    spc: 'M3 3v18h18M6 15l4-6 4 4 6-8',
    articles: 'm12 3 9 5v10l-9 5-9-5V8l9-5M3 8l9 5 9-5M12 13v10M7.5 5.5l9 5',
  };
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      <path d={sciezki[modul]} />
    </svg>
  );
}
