// @ts-check
import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

export default defineConfig({
  site: 'https://www.earnitnotgiven.com',
  trailingSlash: 'ignore',
  build: {
    inlineStylesheets: 'never',
  },
  integrations: [
    sitemap({
      filter: (page) => !page.includes('/admin') && !page.includes('chat-data'),
    }),
  ],
});
