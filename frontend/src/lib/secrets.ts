/** The placeholder the API returns in place of a stored secret (backend app.config.REDACTED). */
export const REDACTED = '***REDACTED***';

/** True when a settings value is the masked placeholder rather than a typed secret. */
export const isMasked = (value: string | null | undefined): boolean => value === REDACTED;
