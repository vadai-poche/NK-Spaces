// Converts/optimizes the raw photos in /Projects into web-ready WebP images in
// /public/projects, and writes a manifest the site reads. Re-run any time you add
// or change source photos:  npm run images
//
// - HEIC and JPG inputs are supported; videos (.mp4/.mov) are ignored.
// - Each photo produces a full-size (max 2000px) and a thumbnail (max 800px) WebP.
// - EXIF orientation is auto-applied; metadata is stripped for privacy + size.

import sharp from 'sharp';
import { readdir, mkdir, writeFile, rm } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const SRC = path.join(root, 'Projects');
const OUT = path.join(root, 'public', 'projects');
const MANIFEST = path.join(root, 'src', 'data', 'generatedProjects.json');

const IMAGE_EXT = new Set(['.jpg', '.jpeg', '.png', '.heic', '.heif']);

const slugify = (s) =>
  s.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');

async function processFolder(folder) {
  const inDir = path.join(SRC, folder);
  const slug = slugify(folder);
  const outDir = path.join(OUT, slug);
  await mkdir(outDir, { recursive: true });

  const files = (await readdir(inDir))
    .filter((f) => IMAGE_EXT.has(path.extname(f).toLowerCase()))
    .sort((a, b) => a.localeCompare(b, undefined, { numeric: true }));

  const images = [];
  let i = 0;
  for (const file of files) {
    i += 1;
    const base = String(i).padStart(2, '0');
    const fullName = `${base}.webp`;
    const thumbName = `${base}-thumb.webp`;
    const input = path.join(inDir, file);

    await sharp(input)
      .rotate()
      .resize({ width: 2000, height: 2000, fit: 'inside', withoutEnlargement: true })
      .webp({ quality: 80 })
      .toFile(path.join(outDir, fullName));

    await sharp(input)
      .rotate()
      .resize({ width: 800, height: 800, fit: 'inside', withoutEnlargement: true })
      .webp({ quality: 72 })
      .toFile(path.join(outDir, thumbName));

    images.push({ full: `/projects/${slug}/${fullName}`, thumb: `/projects/${slug}/${thumbName}` });
    process.stdout.write(`  ${folder}/${file} -> ${fullName}\n`);
  }

  return { folder, slug, count: images.length, images };
}

async function main() {
  if (!existsSync(SRC)) {
    console.error(`No source folder at ${SRC}`);
    process.exit(1);
  }
  // clean previous output
  await rm(OUT, { recursive: true, force: true });
  await mkdir(OUT, { recursive: true });

  const folders = (await readdir(SRC, { withFileTypes: true }))
    .filter((d) => d.isDirectory())
    .map((d) => d.name)
    .sort();

  const manifest = [];
  for (const folder of folders) {
    console.log(`Processing ${folder}...`);
    manifest.push(await processFolder(folder));
  }

  await writeFile(MANIFEST, JSON.stringify(manifest, null, 2));
  console.log(`\nWrote manifest: ${path.relative(root, MANIFEST)}`);
  console.log(manifest.map((m) => `  ${m.folder} (${m.slug}): ${m.count} images`).join('\n'));
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
