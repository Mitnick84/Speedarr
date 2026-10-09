import { describe, expect, it } from 'vitest';
import { REDACTED, isMasked } from '@/lib/secrets';

describe('secrets', () => {
  it('REDACTED equals the wire placeholder', () => {
    expect(REDACTED).toBe('***REDACTED***');
  });

  it('isMasked is true only for the placeholder', () => {
    expect(isMasked(REDACTED)).toBe(true);
    expect(isMasked('')).toBe(false);
    expect(isMasked(null)).toBe(false);
    expect(isMasked(undefined)).toBe(false);
    expect(isMasked('AUDITMARK-typed-secret')).toBe(false);
    expect(isMasked('x***REDACTED***')).toBe(false);
  });
});
