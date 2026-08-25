import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// base: './' — собранный сайт работает из любого подкаталога (хостинг, GitHub Pages).
export default defineConfig({
  plugins: [react()],
  base: './',
})
