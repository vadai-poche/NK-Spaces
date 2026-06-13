import type { ImageSource } from './types';
import { sanityImage } from './sanity';

interface ImageOpts {
  width?: number;
  height?: number;
}

/**
 * Resolve an ImageSource to a usable <img src>. Plain strings (placeholder data)
 * pass through; Sanity image objects are run through the image CDN with sizing.
 */
export function imageUrl(source: ImageSource, opts: ImageOpts = {}): string {
  if (typeof source === 'string') return source;

  const builder = sanityImage(source);
  if (!builder) return '';

  let b = builder.auto('format').fit('max');
  if (opts.width) b = b.width(opts.width);
  if (opts.height) b = b.height(opts.height);
  return b.url();
}
