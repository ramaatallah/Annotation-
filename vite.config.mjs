import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import { crx } from '@crxjs/vite-plugin';
import { readFileSync, existsSync } from 'node:fs';
import { resolve } from 'node:path';

// فحص قراءة ملف manifest.json بأمان لتجنب إيقاف التشغيل
function getManifest() {
  const rootManifestPath = resolve(process.cwd(), 'manifest.json');
  const publicManifestPath = resolve(process.cwd(), 'public/manifest.json');

  if (existsSync(rootManifestPath)) {
    return JSON.parse(readFileSync(rootManifestPath, 'utf-8'));
  } else if (existsSync(publicManifestPath)) {
    return JSON.parse(readFileSync(publicManifestPath, 'utf-8'));
  }
  
  console.warn('⚠️ تنبيه: لم يتم العثور على manifest.json في المجلد الرئيسي أو public. سيتم بناء التطبيق كـ Web App عادياً.');
  return null;
}

const manifest = getManifest();

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    ...(manifest ? [crx({ manifest })] : []),
  ],
  server: {
    port: 5173,
    strictPort: true,
    hmr: {
      port: 5173,
    },
  },
  build: {
    emptyOutDir: true,
    outDir: 'dist',
    rollupOptions: {
      input: {
        panel: 'index.html',
      },
    },
  },
})