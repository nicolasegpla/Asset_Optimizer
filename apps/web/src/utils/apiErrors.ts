/**
 * API error extraction utilities.
 *
 * Moved from App.tsx to allow hooks to import extractApiError without
 * creating a circular dependency (App → useImageProcessing → App).
 */
import { resolveFriendlyErrorCopy } from '../constants/errorCodes';

export interface ApiErrorDetail {
  code?: string;
  message?: string;
}

export interface ApiErrorShape {
  error?: ApiErrorDetail;
}

export interface ApiErrorResponse {
  detail?: ApiErrorShape | ApiErrorShape[] | string;
  error?: ApiErrorDetail;
}

export interface ProcessingError {
  type: 'error';
  code: string;
  hint: string | null;
  message: string;
  title: string;
}

export function extractApiError(payload: ApiErrorResponse): ProcessingError {
  const nestedError =
    typeof payload.detail === 'object' && payload.detail !== null && !Array.isArray(payload.detail)
      ? payload.detail.error
      : undefined;

  const directError = payload.error;
  const resolvedError = nestedError ?? directError;
  const code = resolvedError?.code ?? 'UNKNOWN_ERROR';
  const friendlyCopy = resolveFriendlyErrorCopy(code);

  return {
    type: 'error',
    code,
    hint: friendlyCopy.hint,
    message:
      resolvedError?.message ??
      (typeof payload.detail === 'string' ? payload.detail : 'An unknown error occurred.'),
    title: friendlyCopy.title,
  };
}