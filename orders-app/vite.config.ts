import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

// Приложение публикуется на GitHub Pages по адресу
// https://<логин>.github.io/first_reposirtory/ — поэтому base с именем репозитория.
// Если поменяешь имя репозитория, поменяй строку ниже (и только её).
const base = '/first_reposirtory/'

export default defineConfig({
  base,
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.svg', 'icons/icon-192.png', 'icons/icon-512.png', 'icons/maskable-512.png'],
      workbox: {
        // Кэшируем всё приложение целиком: после первой загрузки оно
        // открывается и работает без интернета.
        globPatterns: ['**/*.{js,css,html,svg,png,woff2}'],
        navigateFallback: base + 'index.html',
        // Рядом с приложением на том же адресе лежат другие сайты:
        // /norma/, /sro/, /pto/, /stroigeroi/. Без этой строки служебный
        // скрипт приложения перехватывал переходы на них и подставлял
        // экран «Заказов» — посетитель открывал ссылку на сайт СРО
        // и попадал в приложение. Эти адреса отдаём сети как есть.
        navigateFallbackDenylist: [new RegExp(`^${base}(norma|sro|pto|stroigeroi)(/|$)`)],
        cleanupOutdatedCaches: true,
        runtimeCaching: [
          {
            // Шрифты Google подтягиваются один раз и дальше живут в кэше.
            urlPattern: /^https:\/\/fonts\.(googleapis|gstatic)\.com\/.*/i,
            handler: 'CacheFirst',
            options: {
              cacheName: 'google-fonts',
              expiration: { maxEntries: 20, maxAgeSeconds: 60 * 60 * 24 * 365 },
              cacheableResponse: { statuses: [0, 200] },
            },
          },
        ],
      },
      manifest: {
        name: 'Заказы',
        short_name: 'Заказы',
        description: 'Учёт заказов фрилансера: деньги, сроки, клиенты и источники',
        lang: 'ru',
        start_url: base,
        scope: base,
        display: 'standalone',
        orientation: 'portrait',
        background_color: '#F7F8FA',
        theme_color: '#4A6FE3',
        categories: ['business', 'productivity', 'finance'],
        icons: [
          { src: 'icons/icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: 'icons/icon-512.png', sizes: '512x512', type: 'image/png' },
          { src: 'icons/maskable-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
      },
      devOptions: { enabled: false },
    }),
  ],
})
