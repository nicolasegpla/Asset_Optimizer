/**
 * Threshold-based caution warnings for large batch selections.
 * Thresholds are 50% of hard limits (file count and total bytes).
 */

export type WarningLevel = "caution";

export interface BatchWarning {
  level: WarningLevel;
  message: string;
}

/**
 * Given current file count, total bytes, and backend limits,
 * return caution-level warning objects.
 * Warnings do NOT block submission — only hard-limit errors do.
 */
export function computeBatchWarnings(
  fileCount: number,
  totalBytes: number,
  limits: { max_files: number; max_total_bytes: number },
): BatchWarning[] {
  const warnings: BatchWarning[] = [];

  const FILE_COUNT_CAUTION_THRESHOLD = Math.floor(limits.max_files / 2); // 50
  const SIZE_CAUTION_THRESHOLD = Math.floor(limits.max_total_bytes / 2); // 25 MB

  if (fileCount >= FILE_COUNT_CAUTION_THRESHOLD) {
    warnings.push({
      level: "caution",
      message: `You're optimizing a large batch (${fileCount} files). Processing may take longer.`,
    });
  }

  if (totalBytes >= SIZE_CAUTION_THRESHOLD) {
    const sizeMB = Math.round(totalBytes / 1024 / 1024);
    warnings.push({
      level: "caution",
      message: `Total size is ${sizeMB} MB. Large batches may take longer to process.`,
    });
  }

  return warnings;
}