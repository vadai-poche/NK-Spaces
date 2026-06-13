// Shared content types. These mirror the Sanity schema so we can swap the local
// placeholder data for live Sanity content without changing any page templates.

/** An image is either a plain URL (placeholder data) or a Sanity image object. */
export type ImageSource = string | { asset?: unknown; alt?: string; caption?: string };

export interface GalleryImage {
  src: ImageSource;
  alt: string;
  caption?: string;
}

export interface Project {
  kind: 'interior' | 'art' | 'painting';
  group: 'interior' | 'makeover';
  title: string;
  slug: string;
  location: string;
  year: string;
  category: string;
  coverImage: ImageSource;
  gallery: GalleryImage[];
  description: string[];
  beforeImage?: ImageSource;
  afterImage?: ImageSource;
  tourVideo?: string; // URL/path to a full house-tour video
  featured: boolean;
  order: number;
}

export interface SocialLink {
  label: string;
  url: string;
}

export interface SiteSettings {
  name: string;
  tagline: string;
  founder: string;
  aboutHeadline: string;
  about: string[];
  heroImage?: ImageSource; // homepage hero banner; falls back to the lead project's first photo
  ownerPhoto: ImageSource;
  services: { title: string; description: string }[];
  phone: string;
  whatsapp: string; // digits only, e.g. 919900000000
  email: string;
  socials: SocialLink[];
  serviceArea: string;
}
