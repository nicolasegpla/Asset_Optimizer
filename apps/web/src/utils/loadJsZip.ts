/**
 * Thin async adapter for JSZip.
 *
 * Extracts the dynamic import behind this function so that tests can
 * mock the entire module rather than the `jszip` package directly.
 * This gives deterministic unit isolation without dealing with
 * import-time side effects.
 */

let _jszipModule: typeof import('jszip') | null = null;

export async function loadJsZip(): Promise<typeof import('jszip')> {
  if (_jszipModule === null) {
    const JSZip = (await import('jszip')).default;
    _jszipModule = JSZip;
  }
  return _jszipModule;
}