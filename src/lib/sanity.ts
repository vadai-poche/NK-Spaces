import { createClient } from '@sanity/client';
import imageUrlBuilder from '@sanity/image-url';

// These come from environment variables once you create a Sanity project.
// Until then they are empty and the site falls back to local placeholder data.
const projectId = import.meta.env.PUBLIC_SANITY_PROJECT_ID ?? '';
const dataset = import.meta.env.PUBLIC_SANITY_DATASET ?? 'production';

export const isSanityConfigured = projectId.length > 0;

export const sanityClient = isSanityConfigured
  ? createClient({
      projectId,
      dataset,
      apiVersion: '2024-01-01',
      useCdn: true,
    })
  : null;

const builder = sanityClient ? imageUrlBuilder(sanityClient) : null;

/** Build a URL for a Sanity image object. Returns null if Sanity is not configured. */
export function sanityImage(source: unknown) {
  return builder ? builder.image(source as never) : null;
}
