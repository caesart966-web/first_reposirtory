import { resolve } from 'node:path'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// base: './' — собранный сайт работает из любого подкаталога (хостинг, GitHub Pages).
//
// Точек входа четыре: главная и три страницы видов СРО. Каждая — обычный
// статический html со своим адресом: роутера в браузере нет, поэтому ссылки
// работают и без JS, поисковик видит три отдельные страницы, а хостингу не
// нужен фолбэк на index.html. Рукописные пути внутри компонентов (картинки
// из public/, якоря на секции главной) знают о своей глубине через
// src/lib/site.ts — см. комментарий там.
export default defineConfig({
  plugins: [react()],
  base: './',
  build: {
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'index.html'),
        stroiteli: resolve(__dirname, 'sro-stroiteley/index.html'),
        proektirovshchiki: resolve(__dirname, 'sro-proektirovshchikov/index.html'),
        izyskateli: resolve(__dirname, 'sro-izyskateley/index.html'),
      },
    },
  },
})
