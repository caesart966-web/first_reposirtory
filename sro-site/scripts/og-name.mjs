// Имя картинки страницы для мессенджеров (og:image), 22.10.2026:
// 'uslugi/dokumenty/' → 'uslugi-dokumenty.jpg'. Одна функция на build-og.mjs
// (рисует картинки) и build-articles.mjs (пишет адрес в страницы статей).
export const ogName = (url) => `${url.replace(/\/$/, '').replace(/\//g, '-')}.jpg`
