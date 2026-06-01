/**
 * Backend-aligned limits constants.
 *
 * DEFAULT_LIMITS mirrors the backend's hard-limit defaults so the frontend
 * can render limits info before the first /api/v1/limits call,
 * and silently fall back to these values when the API is unreachable.
 *
 * Must stay in sync with: apps/api/app/schemas.py LimitsResponse defaults.
 */

export interface Limits {
  max_files: number;
  max_total_bytes: number;
  max_pixels: number;
  max_glb_per_file: number;
  max_glb_total_bytes: number;
}

export const DEFAULT_LIMITS: Limits = {
  max_files: 100,
  max_total_bytes: 50 * 1024 * 1024, // 50 MB
  max_pixels: 50 * 1024 * 1024, // 50 MP
  max_glb_per_file: 100 * 1024 * 1024, // 100 MB
  max_glb_total_bytes: 500 * 1024 * 1024, // 500 MB
};