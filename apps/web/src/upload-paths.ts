/**
 * Build the `paths` multipart field value for folder/batch uploads.
 *
 * Returns a JSON-serialized ordered array of source-relative paths, one per
 * file, in the same order files are appended to FormData.
 * Returns `null` when all files have no folder path segment (flat upload).
 *
 * Canonical payload shape: `["subdir/file.jpg", "other/img.png"]`
 * Legacy shape (not produced here): `{ "file.jpg": "subdir/file.jpg" }`
 *
 * Path normalization rules (mirrored in backend `upload_paths.py`):
 * - Backslash (`\`) → forward slash (`/`)
 * - Strip empty and bare `.` segments
 * - Strip leading `./`
 * - Drive prefixes rejected at API layer
 */
export function buildPathsPayload(files: File[]): string | null {
    const paths: string[] = [];

    for (const file of files) {
        const raw = file.webkitRelativePath || file.name;

        // Normalize backslashes to forward slashes
        const normalized = raw.replace(/\\/g, "/");

        // Strip `.` segments and empty parts, then rebuild path
        const segments = normalized.split("/").filter((seg) => seg && seg !== ".");
        const clean = segments.join("/");

        paths.push(clean);
    }

    // If no file has a path segment beyond its filename, skip the paths field entirely
    const hasFolderSegment = paths.some((p) => p.includes("/"));
    if (!hasFolderSegment) {
        return null;
    }

    return JSON.stringify(paths);
}