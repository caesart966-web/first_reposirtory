// Текст страницы лежит в HTML готовым (scripts/prerender.mjs), но до первой
// отрисовки скриптом спрятан классом pre-wait на <html>: иначе посетитель
// увидел бы его на миг, а затем ту же страницу, собранную заново. Снимается
// сразу после первой отрисовки в каждой точке входа.
export const markMounted = () => document.documentElement.classList.remove('pre-wait')
