// Copies each Updated_images/<code> set into Projects/P<code>, ordered by the
// filename's leading sequence (supports letter inserts like 2a, 5a, 11a), renamed
// to zero-padded sequential names so the image build orders them exactly.
// Re-runnable: it wipes and rewrites each destination folder.
import { copyFile, readdir, rm, mkdir } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const UPDATED = path.join(root, 'Updated_images');

// Manual slot for files that don't carry a usable leading sequence number.
const OVERRIDE = {
  '1205_dining_change.jpeg': [3, ''], // fills the missing "3" slot
};

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-/i;

function sortKey(name) {
  if (OVERRIDE[name]) return OVERRIDE[name];
  // UUID-named (camera/export) files have no intended sequence — send to the end.
  if (UUID_RE.test(name)) return [Number.MAX_SAFE_INTEGER, name];
  const m = name.match(/^(\d+)([a-z]*)/i);
  if (!m) return [Number.MAX_SAFE_INTEGER, name];
  return [parseInt(m[1], 10), m[2].toLowerCase()];
}

const IMAGE_EXT = new Set(['.jpg', '.jpeg', '.png', '.heic', '.heif']);

const codes = (await readdir(UPDATED, { withFileTypes: true }))
  .filter((d) => d.isDirectory())
  .map((d) => d.name);

for (const code of codes) {
  const srcAbs = path.join(UPDATED, code);
  // numeric folder (601, 205…) -> Projects/P601; named folder (P307, Sainiwas) -> as-is
  const destName = /^\d+$/.test(code) ? `P${code}` : code;
  const destAbs = path.join(root, 'Projects', destName);
  const files = (await readdir(srcAbs)).filter(
    (f) => !f.startsWith('.') && IMAGE_EXT.has(path.extname(f).toLowerCase())
  );
  files.sort((a, b) => {
    const [na, la] = sortKey(a);
    const [nb, lb] = sortKey(b);
    return na - nb || String(la).localeCompare(String(lb));
  });

  await rm(destAbs, { recursive: true, force: true });
  await mkdir(destAbs, { recursive: true });
  console.log(`${destName}:`);
  let i = 0;
  for (const f of files) {
    i += 1;
    const ext = path.extname(f).toLowerCase();
    const outName = `${String(i).padStart(2, '0')}${ext}`;
    await copyFile(path.join(srcAbs, f), path.join(destAbs, outName));
    process.stdout.write(`  ${outName}  <-  ${f}\n`);
  }
  console.log(`  (${files.length} images)\n`);
}
