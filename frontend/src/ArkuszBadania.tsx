import type { ReactNode } from 'react';
import { complete, inSpec, type Order, type Plan } from './types';
import './arkuszBadania.css';

type Props = {
  plan: Plan;
  order: Order;
  operator: string;
  values: Record<string, string[]>;
  correctionId?: number;
  onValue: (key: string, index: number, value: string) => void;
};

function Etykieta({ pl, en }: { pl: string; en: string }) {
  return (
    <>
      {pl}
      <small lang="en">{en}</small>
    </>
  );
}

/** Zestawia metrykę, wymagane pomiary i stopkę w układzie arkusza TEST. */
export function ArkuszBadania({ plan, order, operator, values, correctionId, onValue }: Props) {
  const field = (pl: string, en: string, control: ReactNode) => (
    <label className="test-field">
      <span>
        <Etykieta pl={pl} en={en} />
      </span>
      {control}
    </label>
  );
  const date = new Intl.DateTimeFormat('sv-SE').format(new Date());
  return (
    <section className="test-sheet" aria-labelledby="test-report-title">
      <div className="test-report-title">
        <img src="/branding/aunde.png" alt="AUNDE" />
        <h2 id="test-report-title" lang="en">
          Laboratory Performance Test Results
        </h2>
        <span>
          Cykl {plan.cycle} · Wersja {plan.version}
          {correctionId && ` · Korekta #${correctionId}`}
        </span>
      </div>
      <div className="test-metadata">
        <div>
          {field('Organizacja', 'Organization / company', <output>AUNDE Poland</output>)}
          {field('Numer DUNS', 'DUNS number', <output>–</output>)}
          {field('Laboratorium', 'Laboratory', <output>AUNDE Poland</output>)}
          {field('Numer lotto', 'Batch number', <output>{order.lot}</output>)}
          {field('Poziom produkcji', 'Production level', <input name="production_level" />)}
          {field('Numer WZ', 'Delivery note no.', <input name="delivery_note" />)}
        </div>
        <div>
          {field('Numer części klienta', 'Customer part number', <output>–</output>)}
          {field('Nazwa części', 'Part name', <output>{plan.article}</output>)}
          {field('Numer beli', 'Roll no.', <output>{order.roll || '–'}</output>)}
          {field(
            'Data badania',
            'Date',
            <input type="date" name="test_date" required defaultValue={date} />,
          )}
          {field('Kod części AUNDE', 'AUNDE part no.', <output>{plan.code}</output>)}
        </div>
      </div>
      <div
        className="test-table-scroll"
        tabIndex={0}
        role="region"
        aria-label="Tabela pomiarów laboratoryjnych"
      >
        <table className="test-table">
          <colgroup>
            <col className="test-product-col" />
            <col className="test-method-col" />
            <col className="test-standard-col" />
            <col className="test-limit-col" />
            <col className="test-unit-col" />
          </colgroup>
          <colgroup span={3} className="test-points-col" />
          <colgroup>
            <col className="test-average-col" />
            <col className="test-result-col" />
          </colgroup>
          <thead>
            <tr>
              <th scope="col" rowSpan={2}>
                <Etykieta pl="Wyrób" en="Product" />
              </th>
              <th scope="col" rowSpan={2}>
                <Etykieta pl="Rodzaj badań" en="Test description" />
              </th>
              <th scope="col" rowSpan={2}>
                <Etykieta pl="Nr i nazwa normy" en="Test standard" />
              </th>
              <th scope="col" rowSpan={2}>
                <Etykieta pl="Wartość min / max" en="Limits" />
              </th>
              <th scope="col" rowSpan={2}>
                <Etykieta pl="Jednostka" en="Unit" />
              </th>
              <th scope="colgroup" colSpan={3}>
                <Etykieta pl="Wyniki pomiarów" en="Organization measurement results" />
              </th>
              <th scope="col" rowSpan={2}>
                <Etykieta pl="Średnia" en="Average" />
              </th>
              <th scope="col" rowSpan={2}>
                <Etykieta pl="Ocena końcowa" en="Final assessment" />
              </th>
            </tr>
            <tr>
              <th scope="col">
                <Etykieta pl="Str. lewa" en="LH" />
              </th>
              <th scope="col">
                <Etykieta pl="Środek" en="M" />
              </th>
              <th scope="col">
                <Etykieta pl="Str. prawa" en="RH" />
              </th>
            </tr>
          </thead>
          <tbody>
            {plan.specs.map((spec, index) => {
              const points = values[spec.key] || [];
              const filled = complete([spec], values);
              const avg =
                spec.kind === 'numeric' && filled
                  ? points.reduce((sum, val) => sum + Number(val.replace(',', '.')), 0) / spec.count
                  : null;
              const ok =
                filled &&
                (avg === null ? points.every((v) => spec.passing.includes(v)) : inSpec(avg, spec));
              const bounds =
                spec.kind === 'qualitative'
                  ? spec.passing.join(', ')
                  : [
                      spec.lsl === null ? '' : `${spec.lower_inclusive ? '≥' : '>'} ${spec.lsl}`,
                      spec.usl === null ? '' : `${spec.upper_inclusive ? '≤' : '<'} ${spec.usl}`,
                    ]
                      .filter(Boolean)
                      .join(' / ');
              const point = (label: string, i: number) => {
                const value = points[i] ?? '';
                const bad =
                  value !== '' &&
                  (spec.kind === 'numeric'
                    ? !inSpec(Number(value.replace(',', '.')), spec)
                    : !spec.passing.includes(value));
                const input = {
                  'aria-label': `${spec.name} ${label}`,
                  required: true,
                  value,
                  className: bad ? 'outside' : undefined,
                };
                return (
                  <label key={i} className="test-point">
                    <span>{label}</span>
                    {spec.kind === 'numeric' ? (
                      <input
                        {...input}
                        inputMode="decimal"
                        onChange={(e) => onValue(spec.key, i, e.target.value)}
                      />
                    ) : (
                      <select {...input} onChange={(e) => onValue(spec.key, i, e.target.value)}>
                        <option value="">Wybierz</option>
                        {spec.allowed.map((choice) => (
                          <option key={choice}>{choice}</option>
                        ))}
                      </select>
                    )}
                  </label>
                );
              };
              return (
                <tr key={spec.key}>
                  {index === 0 && (
                    <td rowSpan={plan.specs.length} className="test-product">
                      {plan.code}
                      <small>{plan.article}</small>
                    </td>
                  )}
                  <th scope="row">
                    {spec.name}
                    {spec.frequency !== 'every' && (
                      <small>
                        {spec.frequency === 'nth'
                          ? `Co ${spec.every_n}. badanie`
                          : 'Badanie dodatkowe'}
                      </small>
                    )}
                  </th>
                  <td>{spec.method || '–'}</td>
                  <td>{bounds || '–'}</td>
                  <td>{spec.unit || '–'}</td>
                  {spec.count <= 3 ? (
                    Array.from({ length: 3 }, (_, i) => (
                      <td key={i} className={i < spec.count ? 'test-entry' : undefined}>
                        {i < spec.count ? point(spec.labels[i], i) : '–'}
                      </td>
                    ))
                  ) : (
                    <td colSpan={3} className="test-entry">
                      <div className="test-extra-points">{spec.labels.map(point)}</div>
                    </td>
                  )}
                  <td className="test-average">
                    {avg === null
                      ? '–'
                      : avg.toLocaleString('pl-PL', {
                          minimumFractionDigits: spec.decimals,
                          maximumFractionDigits: spec.decimals,
                        })}
                  </td>
                  <td className={`test-assessment ${filled ? (ok ? 'test-ok' : 'test-nok') : ''}`}>
                    {filled ? (ok ? 'OK' : 'NOK') : '–'}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <div className="test-signoff">
        {field('Urządzenie', 'Test equipment', <input name="device" maxLength={250} />)}
        {field('Uwagi', 'Remarks', <textarea name="notes" maxLength={4000} rows={2} />)}
        <div className="test-signoff-grid">
          {field(
            'Data rozpoczęcia badania',
            'Test start date',
            <input name="started_on" type="date" />,
          )}
          {field('Badanie wykonał', 'Test performed by', <output>{operator}</output>)}
          {field(
            'Data zakończenia badania',
            'Test end date',
            <input name="ended_on" type="date" />,
          )}
          {field(
            'Badanie zatwierdził',
            'Approved by',
            <output>Rejestrowane przy zapisie: {operator}</output>,
          )}
        </div>
      </div>
    </section>
  );
}
