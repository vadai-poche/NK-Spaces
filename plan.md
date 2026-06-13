# Interior Design Portfolio Website — Plan

## Context
An interior designer wants a professional website to showcase completed projects from photos,
including one project with a before/after comparison. Requirements:
- Custom-coded site (not a no-code builder), hosted free, paying only for a domain.
- Visitor inquiries arrive as email to the owner.
- The owner can add new projects themselves later (self-service CMS).
- 4–8 projects showcased at launch.

The owner is non-technical, so the build must be low-maintenance, the admin experience simple,
and security handled by managed/free tooling (auto SSL, hosted login).

## Decisions (confirmed)
- **Build:** Custom-coded, free hosting. Domain is the only cost (~₹1,000/yr).
- **Framework:** Astro — built for fast, image-heavy content sites; excellent image
  optimization, great Lighthouse scores, simple deploy.
- **CMS:** Sanity (free tier) — hosted visual Studio the owner logs into to add projects,
  upload photos, and edit text. Has a proper image CDN + cropping and a hosted login. Site
  rebuilds automatically when content changes (deploy webhook).
- **Hosting:** Netlify (free) — automatic HTTPS/SSL, global CDN, built-in form handling.
- **Email inquiries:** Netlify Forms → email to the owner. Plus a WhatsApp click-to-chat
  button and click-to-call.

## Tech stack
- Astro (latest) + Tailwind CSS
- Sanity v3 Studio + `@sanity/client` / `@sanity/image-url`
- `astro:assets` for local image optimization; Sanity image CDN for CMS images
- Deployed to Netlify; DNS pointed from registrar (Cloudflare/Namecheap recommended)

## Site structure
- `/` Home — full-bleed hero image, tagline, featured projects, contact CTA
- `/projects` — gallery grid of all projects
- `/projects/[slug]` — single project: photo gallery, description, and a **before/after
  slider** for projects flagged as such
- `/about` — bio, photo, philosophy, services
- `/contact` — inquiry form + WhatsApp + phone + email + area served
- Shared header/nav + footer; fully mobile-first

## Before / After comparison
- Draggable image-comparison slider on project detail pages (lightweight CSS clip + range
  input, no heavy library).
- Sanity project schema has optional `beforeImage` / `afterImage`; the slider renders only
  when both are present.

## Sanity content model
- `project`: `title`, `slug`, `location`, `year`, `category`, `coverImage`, `gallery`
  (images with caption + alt), `description` (rich text), `beforeImage`, `afterImage`,
  `featured` (boolean), `order`
- `siteSettings` (singleton): studio name, tagline, about text, owner photo, services list,
  phone, WhatsApp number, email, social links, service area
- All copy lives in the CMS so the owner can edit without code.

## Contact form → email
- Netlify Forms `<form data-netlify="true">` with name, phone, email, message, project-type select.
- Email notification configured to the owner's address.
- Honeypot field + Netlify spam filtering; thank-you state after submit.

## Domain & security (one-time setup)
- Buy domain at Cloudflare or Namecheap (~₹800–1,500/yr, **yearly** renewal — enable auto-renew).
- Point DNS to Netlify; Netlify provisions free Let's Encrypt SSL automatically (https padlock).
- Enable 2FA on registrar, Netlify, and Sanity accounts.
- Optionally front with Cloudflare (free) for CDN + basic DDoS protection.
- No sensitive user data stored — main risk is account takeover, covered by 2FA + managed SSL.

## Build steps
1. Scaffold Astro project in this directory; add Tailwind.
2. Base layout, header, footer, global styles, fonts (elegant serif + clean sans).
3. Initialize Sanity project + Studio; define `project` and `siteSettings` schemas; deploy Studio.
4. Wire Astro to Sanity; build queries for projects/settings.
5. Build pages: Home, Projects gallery, Project detail (with before/after slider), About, Contact.
6. Contact form (Netlify Forms) + WhatsApp/call buttons.
7. Responsive polish, SEO meta, Open Graph, favicon, sitemap.
8. Seed with placeholder content, then replace with real photos/text.
9. Deploy to Netlify; connect Sanity deploy webhook for auto-rebuilds.
10. Short README documenting domain purchase, DNS, and form-email setup.

## What I need from you (content)
1. **Business name + tagline** (logo if you have one; otherwise type-based branding).
2. **About text** — a short paragraph about you and your design approach.
3. **Services list** — what you offer.
4. **Project photos** — for each of 4–8 projects: photos + title, location/city, year,
   category, 1–2 sentence description. Mark the before/after project and which photo is
   "before" vs "after".
5. **Contact details** — phone, WhatsApp, inquiry email, social links, city/area served.
6. **Domain preference** — a name you'd like (e.g. `yourname.com`) to check availability.

Photos can be sent as-is; resizing/optimization is handled in the build.

## Verification
- `npm run dev` — review every page on desktop + mobile.
- Confirm before/after slider drags and only shows on the flagged project.
- `npm run build` + `npm run preview` — no broken images/links.
- Submit the contact form on the deployed site; confirm the email arrives.
- Edit a project in Sanity Studio; confirm the site rebuilds and updates.
- Run Lighthouse — target 90+ on Performance/Accessibility/SEO.
- Verify the https:// padlock after DNS + SSL setup.
