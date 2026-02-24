import { defineConfig } from 'vite';
import tailwindcss from '@tailwindcss/vite'

import { resolve } from 'path';
import fs from 'fs';

export default defineConfig({
  base: '/static/vite/',
  build: {
    manifest: true,
    outDir: resolve('../static/vite'),
    rollupOptions: {
      input: {
        main: resolve('./src/main.js')
      }
    }
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    https: fs.existsSync('../.mock_certs/key.pem') && fs.existsSync('../.mock_certs/cert.pem') ? {
      key: fs.readFileSync('../.mock_certs/key.pem'),
      cert: fs.readFileSync('../.mock_certs/cert.pem'),
    } : false,
    origin: 'https://localhost:5173',
    fs: {
      allow: ['..']
    }
  },
  resolve: {
    alias: {
      '@': resolve('./src')
    }
  },
  plugins: [
    tailwindcss(),
  ],
});