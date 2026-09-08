import { resolve } from 'node:path'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// base: './' — собранный сайт работает из любого подкаталога (хостинг, GitHub Pages).
//
// Точек входа одиннадцать: главная, три страницы видов СРО и семь страниц услуг. Каждая — обычный
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
        // Страницы услуг: семь адресов под /uslugi/, точка входа src/service.tsx.
        usluga_vstuplenie: resolve(__dirname, 'uslugi/vstuplenie-v-sro/index.html'),
        usluga_podbor: resolve(__dirname, 'uslugi/podbor-i-proverka-sro/index.html'),
        usluga_dokumenty: resolve(__dirname, 'uslugi/dokumenty/index.html'),
        usluga_nrs: resolve(__dirname, 'uslugi/specialisty-nrs/index.html'),
        usluga_nok: resolve(__dirname, 'uslugi/nok/index.html'),
        usluga_uroven: resolve(__dirname, 'uslugi/uroven-otvetstvennosti/index.html'),
        usluga_proverki: resolve(__dirname, 'uslugi/soprovozhdenie-proverok/index.html'),
      },
    },
  },
})
