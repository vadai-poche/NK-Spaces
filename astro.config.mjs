// @ts-check
import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';
import tailwindcss from '@tailwindcss/vite';

// Update `site` to your final domain before deploying (used for sitemap + canonical URLs).
export default defineConfig({
  site: 'https://nkspaces.in',
  integrations: [sitemap()],
  vite: {
    plugins: [tailwindcss()],
  },
});
