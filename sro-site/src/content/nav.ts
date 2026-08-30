// Разделы страницы в одном месте: их перечисляют и шапка, и подвал, и
// расходиться эти списки не должны — переименованный раздел иначе живёт
// под двумя названиями, а удалённый оставляет ссылку в никуда.
//
// inHeader — не «важность», а вопрос ширины: на 1024-1279px в шапке помещается
// ровно четыре пункта плюс телефон и кнопка (запас на 1440px — около 125px,
// меньше цены пятого пункта). В подвале ограничения нет, там показаны все.
export const SECTIONS = [
  { href: '#types', label: 'Виды СРО', inHeader: false },
  { href: '#services', label: 'Услуги', inHeader: true },
  { href: '#pricing', label: 'Стоимость', inHeader: true },
  { href: '#about', label: 'О специалисте', inHeader: true },
  { href: '#faq', label: 'FAQ', inHeader: true },
  { href: '#contacts', label: 'Контакты', inHeader: false },
] as const

export const HEADER_NAV = SECTIONS.filter((section) => section.inHeader)
