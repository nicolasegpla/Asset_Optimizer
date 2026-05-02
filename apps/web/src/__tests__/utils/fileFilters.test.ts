/**
 * Tests for fileFilters — system/junk file rejection before format validation.
 */
import { describe, it, expect } from 'vitest';
import { filterSystemFiles, SYSTEM_FILE_PATTERNS } from '../../utils/fileFilters';

function makeFile(name: string, size = 1024): File {
  return new File([new ArrayBuffer(size)], name, { type: 'image/png' });
}

describe('filterSystemFiles', () => {
  it('accepts normal image files', () => {
    const files = [makeFile('photo.jpg'), makeFile('Screenshot.png'), makeFile('image.WEBP')];
    const result = filterSystemFiles(files);
    expect(result.filteredCount).toBe(0);
    expect(result.accepted).toHaveLength(3);
  });

  it('rejects .DS_Store', () => {
    const files = [makeFile('.DS_Store'), makeFile('photo.jpg')];
    const result = filterSystemFiles(files);
    expect(result.filteredCount).toBe(1);
    expect(result.filteredNames).toContain('.DS_Store');
    expect(result.accepted).toHaveLength(1);
  });

  it('rejects Thumbs.db', () => {
    const files = [makeFile('Thumbs.db'), makeFile('hero.png')];
    const result = filterSystemFiles(files);
    expect(result.filteredCount).toBe(1);
    expect(result.filteredNames).toContain('Thumbs.db');
  });

  it('rejects desktop.ini', () => {
    const files = [makeFile('desktop.ini'), makeFile('banner.jpg')];
    const result = filterSystemFiles(files);
    expect(result.filteredCount).toBe(1);
    expect(result.filteredNames).toContain('desktop.ini');
  });

  it('rejects files with ._ prefix (macOS resource fork)', () => {
    const files = [makeFile('._meta.json'), makeFile('img.png')];
    const result = filterSystemFiles(files);
    expect(result.filteredCount).toBe(1);
    expect(result.filteredNames).toContain('._meta.json');
  });

  it('rejects files inside __MACOSX folder (webkitRelativePath)', () => {
    const file = makeFile('image.png') as File & { webkitRelativePath: string };
    file.webkitRelativePath = '__MACOSX/subdir/image.png';
    const result = filterSystemFiles([file]);
    expect(result.filteredCount).toBe(1);
  });

  it('rejects files inside .git folder', () => {
    const file = makeFile('config') as File & { webkitRelativePath: string };
    file.webkitRelativePath = '.git/config';
    const result = filterSystemFiles([file]);
    expect(result.filteredCount).toBe(1);
  });

  it('rejects files inside .vscode folder', () => {
    const file = makeFile('settings.json') as File & { webkitRelativePath: string };
    file.webkitRelativePath = '.vscode/settings.json';
    const result = filterSystemFiles([file]);
    expect(result.filteredCount).toBe(1);
  });

  it('returns all rejected names in filteredNames', () => {
    const files = [
      makeFile('.DS_Store'),
      makeFile('Thumbs.db'),
      makeFile('photo.jpg'),
    ];
    const result = filterSystemFiles(files);
    expect(result.filteredNames).toContain('.DS_Store');
    expect(result.filteredNames).toContain('Thumbs.db');
    expect(result.filteredNames).not.toContain('photo.jpg');
  });

  it('handles empty input', () => {
    const result = filterSystemFiles([]);
    expect(result.filteredCount).toBe(0);
    expect(result.accepted).toHaveLength(0);
    expect(result.filteredNames).toHaveLength(0);
  });

  it('accepts hidden files that are not in blocklist', () => {
    const files = [makeFile('.env'), makeFile('.gitignore')];
    const result = filterSystemFiles(files);
    // .env and .gitignore are not in any blocklist segment
    expect(result.filteredCount).toBe(0);
    expect(result.accepted).toHaveLength(2);
  });
});