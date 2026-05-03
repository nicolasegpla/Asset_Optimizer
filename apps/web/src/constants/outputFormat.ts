export const OUTPUT_FORMAT = {
  JPG: 'jpg',
  PNG: 'png',
  WEBP: 'webp',
  AVIF: 'avif',
} as const;

export type OutputFormat = (typeof OUTPUT_FORMAT)[keyof typeof OUTPUT_FORMAT];
