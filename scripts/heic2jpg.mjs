// One-off: convert HEIC/HEIF source photos in Projects/ to JPG (full resolution,
// auto-oriented) and remove the originals. Safe to delete this file after use.
import sharp from 'sharp';
import { readdir, unlink } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const SRC = path.join(root, 'Projects');

const dirs = (await readdir(SRC, { withFileTypes: true }))
  .filter((d) => d.isDirectory())
  .map((d) => path.join(SRC, d.name));

let converted = 0;
for (const dir of dirs) {
  const files = (await readdir(dir)).filter((f) => /\.hei[cf]$/i.test(f));
  for (const f of files) {
    const src = path.join(dir, f);
    const out = path.join(dir, f.replace(/\.hei[cf]$/i, '.jpg'));
    await sharp(src).rotate().jpeg({ quality: 95, mozjpeg: true }).toFile(out);
    await unlink(src);
    converted += 1;
    process.stdout.write(`  ${path.relative(root, src)} -> ${path.basename(out)}\n`);
  }
}
console.log(`\nConverted ${converted} HEIC file(s) to JPG.`);
