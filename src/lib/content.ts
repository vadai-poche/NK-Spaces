import type { Project, SiteSettings } from './types';
import { isSanityConfigured, sanityClient } from './sanity';
import { siteSettings as localSettings } from '../data/siteSettings';
import { projectMeta } from '../data/projectMeta';
import manifest from '../data/generatedProjects.json';

// Single source of truth for content. Today it builds Projects from local photos
// (the generated manifest) + editable metadata. Once Sanity is connected (env vars
// set), it fetches live content instead — no page template needs to change.

interface ManifestEntry {
  folder: string;
  slug: string;
  count: number;
  images: { full: string; thumb: string }[];
}

function buildLocalProjects(): Project[] {
  const entries = manifest as ManifestEntry[];
  return entries
    .filter((e) => projectMeta[e.folder] && e.images.length > 0)
    .map((e) => {
      const meta = projectMeta[e.folder];
      const pick = (idx?: number) =>
        idx && e.images[idx - 1] ? e.images[idx - 1] : undefined;
      const cover = pick(meta.coverIndex) ?? e.images[0];
      const before = pick(meta.beforeIndex);
      const after = pick(meta.afterIndex);
      const galleryImages = meta.photoLimit
        ? e.images.slice(0, meta.photoLimit)
        : e.images;

      return {
        kind: meta.kind ?? 'interior',
        group: meta.group ?? 'interior',
        title: meta.title,
        slug: meta.slug ?? e.slug,
        tourVideo: meta.tourVideo,
        location: meta.location,
        year: meta.year,
        category: meta.category,
        coverImage: meta.coverImageSrc ?? cover.thumb,
        gallery: galleryImages.map((img, i) => ({
          src: img.full,
          alt: `${meta.title} — photo ${i + 1}`,
        })),
        description: meta.description,
        beforeImage: before?.full,
        afterImage: after?.full,
        featured: meta.featured,
        order: meta.order,
      } satisfies Project;
    })
    .sort((a, b) => a.order - b.order);
}

export async function getSiteSettings(): Promise<SiteSettings> {
  if (isSanityConfigured && sanityClient) {
    const data = await sanityClient.fetch(`*[_type == "siteSettings"][0]`);
    if (data) return data as SiteSettings;
  }
  return localSettings;
}

// All entries (interiors + art), used for slug lookups.
async function getAllEntries(): Promise<Project[]> {
  if (isSanityConfigured && sanityClient) {
    const data = await sanityClient.fetch(`*[_type == "project"] | order(order asc)`);
    if (data?.length) return data as Project[];
  }
  return buildLocalProjects();
}

// Interior design projects only (the "Projects" section).
export async function getProjects(): Promise<Project[]> {
  const all = await getAllEntries();
  return all.filter((p) => p.kind === 'interior');
}

// Resin art (its own section).
export async function getArtworks(): Promise<Project[]> {
  const all = await getAllEntries();
  return all.filter((p) => p.kind === 'art');
}

// Paintings (its own section).
export async function getPaintings(): Promise<Project[]> {
  const all = await getAllEntries();
  return all.filter((p) => p.kind === 'painting');
}

export interface CarouselImage {
  src: string;
  alt: string;
}

// Balcony photos pulled from across projects (set via balconyIndices in projectMeta),
// for the home "Balcony Makeover" carousel. Local-data only.
export function getBalconyImages(): CarouselImage[] {
  const entries = manifest as ManifestEntry[];
  const out: CarouselImage[] = [];
  for (const e of entries) {
    const meta = projectMeta[e.folder];
    if (!meta?.balconyIndices) continue;
    for (const idx of meta.balconyIndices) {
      const img = e.images[idx - 1];
      if (img) out.push({ src: img.full, alt: `${meta.title} — balcony` });
    }
  }
  return out;
}

export async function getFeaturedProjects(): Promise<Project[]> {
  const projects = await getProjects();
  const featured = projects.filter((p) => p.featured);
  return featured.length ? featured : projects.slice(0, 3);
}

export async function getProjectBySlug(slug: string): Promise<Project | undefined> {
  const all = await getAllEntries();
  return all.find((p) => p.slug === slug);
}
