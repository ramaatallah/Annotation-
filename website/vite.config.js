import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  base: './', // عشان النسخة المبنية تشتغل من أي مسار (GitHub Pages، فتح dist مباشرة...)
})
