/**
 * System and junk file filtering before format validation.
 *
 * Order: run filterSystemFiles FIRST, then validate supported input format.
 * This avoids junk/system files surfacing as "unsupported format" errors.
 *
 * Patterns:
 * - Exact basename: .DS_Store, Thumbs.db, desktop.ini
 * - Basename prefix: ._  (macOS resource fork)
 * - Path segment: __MACOSX, .git, .vscode
 * - Hidden files (basename starts with .) that don't match above are kept.
 */
export interface FileFilterPatterns {
  exactBasenames: readonly string[];
  basenamePrefixes: readonly string[];
  pathSegments: readonly string[];
}

export const SYSTEM_FILE_PATTERNS: FileFilterPatterns = {
  exactBasenames: ['.DS_Store', 'Thumbs.db', 'desktop.ini'],
  basenamePrefixes: ['._'],
  pathSegments: ['__MACOSX', '.git', '.vscode'],
} as const;

function isSystemFile(file: File): boolean {
  const name = file.name;
  const lowerName = name.toLowerCase();

  // Exact basename match (case-insensitive)
  if (SYSTEM_FILE_PATTERNS.exactBasenames.some((n) => n.toLowerCase() === lowerName)) {
    return true;
  }

  // Basename prefix match (case-insensitive)
  if (SYSTEM_FILE_PATTERNS.basenamePrefixes.some((prefix) => lowerName.startsWith(prefix.toLowerCase()))) {
    return true;
  }

  // Path segment match — check if any path segment matches
  // For File inputs, webkitRelativePath contains the full path
  const fullPath = (file as File & { webkitRelativePath?: string }).webkitRelativePath || name;
  const pathParts = fullPath.split('/');
  if (pathParts.some((seg) => SYSTEM_FILE_PATTERNS.pathSegments.includes(seg))) {
    return true;
  }

  return false;
}

export interface FileFilterResult {
  accepted: File[];
  filteredCount: number;
  filteredNames: string[];
}

/**
 * Filter out junk/system files from a FileList.
 * Returns accepted files plus metadata about what was filtered.
 */
export function filterSystemFiles(files: FileList | File[]): FileFilterResult {
  const allFiles = Array.from(files);
  const junkFiles: File[] = [];
  const acceptedFiles: File[] = [];

  for (const file of allFiles) {
    if (isSystemFile(file)) {
      junkFiles.push(file);
    } else {
      acceptedFiles.push(file);
    }
  }

  return {
    accepted: acceptedFiles,
    filteredCount: junkFiles.length,
    filteredNames: junkFiles.map((f) => f.name),
  };
}