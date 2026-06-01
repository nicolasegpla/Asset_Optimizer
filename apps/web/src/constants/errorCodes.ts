/**
 * Frontend copy map for all known error codes.
 *
 * Includes both server-emitted codes (from backend ErrorCode enum)
 * and client-only codes that the frontend may surface locally.
 *
 * Mirror of: apps/api/app/schemas.py ErrorCode enum + client augment.
 */

export const ERROR_COPY = {
  AVIF_UNAVAILABLE: {
    hint: 'AVIF encoding is not available in this runtime environment.',
    title: 'AVIF encoding not available',
  },
  FILE_COUNT_LIMIT: {
    hint: 'Try a smaller batch with fewer than 100 files.',
    title: 'Too many files selected',
  },
  GLB_OPTIMIZATION_FAILED: {
    hint: 'Make sure the file is a valid GLB and try again.',
    title: 'GLB optimization failed',
  },
  GLB_RUNTIME_UNAVAILABLE: {
    hint: 'The GLB optimization runtime is not installed on the server.',
    title: 'GLB optimizer not available',
  },
  GLB_TOO_LARGE: {
    hint: 'Try a smaller GLB file or reduce mesh complexity before uploading.',
    title: 'The GLB file is too large',
  },
  INVALID_GLB: {
    hint: 'Make sure the selected files are valid GLB files and not corrupted.',
    title: 'We could not process one or more GLB files',
  },
  IMAGE_TOO_LARGE: {
    hint: 'Try a smaller image or reduce dimensions before uploading.',
    title: 'The image is too large to process',
  },
  INVALID_DIMENSIONS: {
    hint: 'Use width and height values between 1 and 10000 pixels.',
    title: 'The resize dimensions are invalid',
  },
  INVALID_IMAGE: {
    hint: 'Make sure the selected files are real, supported images and not corrupted system files.',
    title: 'We could not process one or more images',
  },
  INVALID_PATHS_FORMAT: {
    hint: 'Try selecting the folder again so we can rebuild its internal structure correctly.',
    title: 'We could not read the folder structure',
  },
  INVALID_QUALITY: {
    hint: 'Choose a quality value between 1 and 100.',
    title: 'The quality value is not valid',
  },
  MIXED_FILE_TYPES: {
    hint: 'Upload only image files or only GLB files, not both at the same time.',
    title: 'Mixed file types are not supported',
  },
  NETWORK_ERROR: {
    hint: 'Check that the API is running and try again.',
    title: 'We could not reach the server',
  },
  PROCESSING_TIMEOUT: {
    hint: 'Try fewer files, smaller images, or a faster output format.',
    title: 'The transformation took too long',
  },
  TOTAL_SIZE_LIMIT: {
    hint: 'Reduce the number of files or use smaller images before uploading.',
    title: 'The upload is too large',
  },
  UNSUPPORTED_INPUT_FORMAT: {
    hint: 'Use JPG, JPEG, PNG, or WEBP files only.',
    title: 'Some selected files are not supported',
  },
  UNSUPPORTED_INPUT_SELECTION: {
    hint: 'Remove unsupported files and keep only JPG, JPEG, PNG, or WEBP images.',
    title: 'Your selection contains unsupported files',
  },
  UNSUPPORTED_OUTPUT_FORMAT: {
    hint: 'Pick one of the formats available in the output selector.',
    title: 'The output format is not available',
  },
  UNKNOWN_ERROR: {
    hint: 'Please try again. If it keeps happening, review the selected files and settings.',
    title: 'Something went wrong',
  },
} as const;

export type ErrorCodeKey = keyof typeof ERROR_COPY;

function isErrorCodeKey(code: string): code is ErrorCodeKey {
  return code in ERROR_COPY;
}

export function resolveFriendlyErrorCopy(code: string): (typeof ERROR_COPY)[ErrorCodeKey] {
  const key: ErrorCodeKey = isErrorCodeKey(code) ? code : 'UNKNOWN_ERROR';
  return ERROR_COPY[key];
}
