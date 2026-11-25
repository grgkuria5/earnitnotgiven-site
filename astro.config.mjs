// @ts-check
import fs from 'node:fs';
import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

function hex(value, fallback) {
  return /^#[0-9a-fA-F]{6}$/.test(String(value || '')) ? String(value) : fallback;
}

function seconds(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return 16;
  return Math.min(20, Math.max(12, Math.round(n)));
}

function shiftVars() {
  return {
    name: 'shift-vars',
    hooks: {
      'astro:config:setup'({ updateConfig }) {
        updateConfig({
          vite: {
            plugins: [
              {
                name: 'shift-vars-css',
                resolveId(id) {
                  if (id === 'virtual:shift.css') return '\0shift.css';
                },
                load(id) {
                  if (id !== '\0shift.css') return;
                  let raw = {};
                  try {
                    raw = JSON.parse(fs.readFileSync(new URL('./data/settings.json', import.meta.url), 'utf8'));
                  } catch {
                    raw = {};
                  }
                  const gold = hex(raw.shift_gold, '#e0b45a');
                  const blue = hex(raw.shift_blue, '#1c3f73');
                  const teal = hex(raw.shift_teal, '#1f7a72');
                  return `:root{--shift-gold:${gold};--shift-blue:${blue};--shift-teal:${teal};--shift-seconds:${seconds(raw.color_shift_seconds)}s}`;
                },
              },
            ],
          },
        });
      },
    },
  };
}

export default defineConfig({
  site: 'https://www.earnitnotgiven.com',
  trailingSlash: 'ignore',
  build: {
    inlineStylesheets: 'never',
  },
  integrations: [
    shiftVars(),
    sitemap({
      filter: (page) => !page.includes('/admin') && !page.includes('chat-data'),
    }),
  ],
});
