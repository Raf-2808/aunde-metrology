// Napis pozostaje nieruchomy, a południki globusa obracają się w jego obrysie.
export function LogoAunde({ staticLogo = false }: { staticLogo?: boolean }) {
  if (staticLogo) return <img className="brand-logo" src="/branding/aunde.png" alt="AUNDE" />;
  return (
    <div className="brand-logo" role="img" aria-label="AUNDE">
      <img className="brand-wordmark" src="/branding/aunde.png" alt="" aria-hidden="true" />
      <svg
        className="brand-globe"
        viewBox="0 0 64 64"
        fill="none"
        stroke="#243e82"
        strokeWidth="2"
        aria-hidden="true"
      >
        <circle cx="32" cy="32" r="29" />
        <ellipse cx="32" cy="32" rx="29" ry="12" />
        <path d="M7 17 Q32 27 57 17 M7 47 Q32 37 57 47 M3 32 H61" />
        {[0, 1, 2].map((n) => (
          <ellipse
            className="brand-meridian"
            key={n}
            cx="32"
            cy="32"
            rx="14"
            ry="29"
            style={{ animationDelay: `${n * -2}s` }}
          />
        ))}
      </svg>
    </div>
  );
}
