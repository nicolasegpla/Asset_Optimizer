/// <reference types="vitest" />
import { defineConfig } from 'vite';

export default defineConfig({
  test: {
    environment: 'happy-dom',
    setupFiles: ['./src/__tests__/setup.ts'],
    include: ['src/__tests__/**/*.test.{ts,tsx}'],
    coverage: {
      include: ['src/hooks/**', 'src/utils/**', 'src/components/**'],
      exclude: ['src/**/*.d.ts', 'src/__tests__/**'],
    },
  },
});
