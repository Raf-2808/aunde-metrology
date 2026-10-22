import { describe, it, expect } from 'vitest';
import { complete, inSpec, Spec } from './types';
const s: Spec = {
  key: 't',
  name: 'Thickness',
  method_id: 1,
  unit: 'mm',
  kind: 'numeric',
  count: 3,
  labels: ['LH', 'M', 'RH'],
  lsl: '3.2',
  usl: '3.8',
  lower_inclusive: true,
  upper_inclusive: true,
  decimals: 2,
  frequency: 'every',
  every_n: 1,
  allowed: [],
  passing: [],
  simulation_offset: null,
};
describe('Walidacja formularza', () => {
  it('wymaga każdego z dziesięciu pomiarów', () => {
    const a = { ...s, count: 10 };
    expect(complete([a], { t: Array(9).fill('3.5') })).toBe(false);
    expect(complete([a], { t: Array(10).fill('3.5') })).toBe(true);
  });
  it('nie myli pustego pola z zerem', () => {
    expect(complete([s], { t: ['3.5', '', '3.5'] })).toBe(false);
    expect(complete([s], { t: ['0', '3.5', '3.5'] })).toBe(true);
  });
  it('obsługuje przecinek i operatory granic', () => {
    expect(complete([s], { t: ['3,5', '3,4', '3,3'] })).toBe(true);
    expect(inSpec(3.2, s)).toBe(true);
    expect(inSpec(3.2, { ...s, lower_inclusive: false })).toBe(false);
  });
});
