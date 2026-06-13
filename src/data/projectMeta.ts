// Editable metadata for each project, keyed by the SOURCE FOLDER name in /Projects.
// The photos themselves come from the generated manifest (npm run images); this file
// supplies the words + which photo is the cover / before / after.
//
// TODO (need from client): real display titles, locations, years, and a 1–2 line
// description for each. Mark the before/after project with beforeIndex + afterIndex
// (1-based positions in that folder's sorted photo list).

export interface ProjectMeta {
  kind?: 'interior' | 'art' | 'painting'; // 'interior'=Projects, 'art'=Resin Art, 'painting'=Paintings
  group?: 'interior' | 'makeover'; // home grouping: 'interior' (Full Interiors) or 'makeover'
  slug?: string; // public URL slug; defaults to the folder slug. Set to hide internal codes.
  tourVideo?: string; // path/URL to a full house-tour video
  title: string;
  location: string;
  year: string;
  category: string;
  description: string[];
  featured: boolean;
  order: number;
  coverIndex?: number; // 1-based; defaults to first photo
  coverImageSrc?: string; // explicit cover image path (overrides coverIndex)
  beforeIndex?: number; // 1-based position of the "before" photo
  afterIndex?: number; // 1-based position of the "after" photo
  photoLimit?: number; // show at most this many gallery photos
  balconyIndices?: number[]; // 1-based photos used in the home "Balcony Makeover" carousel
}

export const projectMeta: Record<string, ProjectMeta> = {
  Sainiwas: {
    slug: 'residence-1',
    tourVideo: '/tours/residence-1-tour.mp4',
    coverImageSrc: '/featured/sainiwas-cover.webp', // keep the previous cover image
    title: 'Full House (3BHK)',
    location: '',
    year: '',
    category: '',
    description: [
      'A complete home transformation — warm, inviting, and full of personal character.',
    ],
    featured: true,
    order: 1,
    balconyIndices: [15, 16],
  },
  P1205: {
    slug: 'residence-2',
    title: 'Full House (3BHK)',
    location: '',
    year: '',
    category: '',
    description: ['A considered, contemporary home designed around everyday comfort.'],
    featured: true,
    order: 2,
    coverIndex: 3, // use the tv unit photo as the cover (foyer is #1)
    balconyIndices: [15, 16, 17],
  },
  P601: {
    slug: 'residence-3',
    title: 'Full House (3BHK)',
    location: '',
    year: '',
    category: '',
    description: ['Warm interiors balancing clean lines with handcrafted detail.'],
    featured: true,
    order: 3,
    balconyIndices: [13, 14],
  },
  P1202: {
    slug: 'residence-7',
    title: 'Makeover (3BHK)',
    location: '',
    year: '',
    category: '',
    description: ['A full 3BHK renovation — reworked and refreshed end to end.'],
    featured: false,
    order: 8,
    group: 'makeover',
  },
  P307: {
    slug: 'residence-4',
    title: 'Full House (2BHK)',
    location: '',
    year: '',
    category: '',
    description: ['A bright, personality-filled home styled corner to corner.'],
    featured: false,
    order: 5,
  },
  P1105: {
    slug: 'residence-5',
    title: 'Makeover (3BHK)',
    location: '',
    year: '',
    category: '',
    description: ['Cozy, characterful spaces tailored to how the family lives.'],
    featured: false,
    order: 6,
    group: 'makeover',
    balconyIndices: [6, 7],
  },
  P205: {
    slug: 'residence-6',
    title: 'Makeover (3BHK)',
    location: '',
    year: '',
    category: '',
    description: ['Thoughtful styling and décor bringing warmth to every room.'],
    featured: false,
    order: 7,
    group: 'makeover',
  },
  'Resin Art': {
    kind: 'art',
    title: 'Resin Art',
    location: '',
    year: '',
    category: 'Resin & Art',
    description: [
      'Handcrafted resin art — one-of-a-kind pieces made to add colour, texture, and character to a space.',
      'Each work is created by hand and can be commissioned in custom sizes and palettes to suit your home.',
    ],
    featured: false,
    order: 1,
  },
  Paintings: {
    kind: 'painting',
    title: 'Paintings',
    location: '',
    year: '',
    category: 'Paintings',
    description: [
      'Original paintings to bring colour, character, and a personal story to your walls.',
      'Each piece is hand-painted and available as a ready work or a custom commission.',
    ],
    featured: false,
    order: 1,
  },
};
