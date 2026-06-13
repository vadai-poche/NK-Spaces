# NK Studio — Website

Interior design portfolio for **NK Studio** (Nirupama). Built with [Astro](https://astro.build)
+ Tailwind CSS. Fast, static, image-focused. Hosting is free; the only cost is the domain.

## Run locally

```bash
npm install
npm run dev      # http://localhost:4321
npm run build    # production build into dist/
npm run preview  # serve the production build
```

Requires Node 20+.

## Project photos

Raw photos live in `/Projects/<FolderName>/` (one folder per home). To convert + optimize
them for the web (HEIC → WebP, resized, EXIF stripped):

```bash
npm run images
```

This writes optimized images to `public/projects/<slug>/` and a manifest to
`src/data/generatedProjects.json`. Re-run it whenever you add or change photos.

## Editing project details (titles, descriptions, before/after)

Edit `src/data/projectMeta.ts`. Each entry is keyed by the source folder name and controls
the title, location, year, category, description, ordering, which photo is the cover, and
the **before/after** slider:

```ts
P307: {
  title: 'Residence 307',
  ...
  coverIndex: 2,    // 1-based: use the 2nd photo as the cover
  beforeIndex: 5,   // show the before/after slider using photos #5 and #6
  afterIndex: 6,
},
```

The before/after slider appears automatically on a project once `beforeIndex` and
`afterIndex` are set.

## Site text & contact details

Edit `src/data/siteSettings.ts` — studio name, tagline, about text, services, phone,
WhatsApp number (digits only, e.g. `919900000000`), email, social links, service area.

## Contact form → email

The contact form uses **Netlify Forms**. After deploying to Netlify:
1. Submit the form once so Netlify registers it.
2. In Netlify: **Forms → Settings → Form notifications → Add email notification**, pointing
   to Nirupama's inbox. Submissions then arrive by email (spam filtered + honeypot protected).

## Deploy (Netlify, free)

1. Push this folder to a GitHub repo.
2. In Netlify: **Add new site → Import from Git**, pick the repo. Build settings are already
   in `netlify.toml` (`npm run build`, publish `dist`).
3. Add your domain under **Domain settings**; Netlify provisions a free SSL certificate.

## Domain & security

- Domain (`nkspaces.in`) is a **yearly** cost (~₹1,000/yr). Enable
  auto-renew. Point its DNS to Netlify (Netlify gives the exact records).
- HTTPS/SSL is automatic and free on Netlify.
- Enable 2-factor authentication on the domain registrar, Netlify, and (later) Sanity.

## Optional: connect a CMS later (Sanity)

The content layer (`src/lib/content.ts`) already supports Sanity. When ready to let Nirupama
edit projects herself in a browser, set these env vars and the site switches automatically:

```
PUBLIC_SANITY_PROJECT_ID=...
PUBLIC_SANITY_DATASET=production
```

(Schemas and a Studio still need to be created with a Sanity login — a follow-up step.)

## Structure

```
Projects/                 raw source photos (per home)
scripts/process-images.mjs photo optimizer
src/
  data/                   siteSettings, projectMeta, generated manifest
  lib/                    content layer, types, image + sanity helpers
  components/             Header, Footer, ProjectCard, BeforeAfterSlider
  layouts/Layout.astro    page shell (SEO, fonts, header/footer)
  pages/                  index, projects, projects/[slug], about, contact, thank-you
public/projects/          optimized web images (generated)
```
