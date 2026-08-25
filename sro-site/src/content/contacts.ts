// Единая точка правды для персональных данных сайта.
// Замените значения-заглушки на реальные — весь сайт обновится автоматически.
export const CONTACTS = {
  name: '[ИМЯ]',
  role: 'Эксперт по СРО',
  city: '[ГОРОД]',
  phone: '[ТЕЛЕФОН]', // формат: +7 900 000-00-00
  email: '[EMAIL]', // формат: name@domain.ru
  whatsapp: '[WHATSAPP_LINK]', // формат: https://wa.me/79000000000
  max: '[MAX_LINK]', // формат: ссылка на профиль в MAX
} as const

const isPlaceholder = (value: string) => value.startsWith('[') && value.endsWith(']')

export const CONFIGURED = {
  phone: !isPlaceholder(CONTACTS.phone),
  email: !isPlaceholder(CONTACTS.email),
  whatsapp: !isPlaceholder(CONTACTS.whatsapp),
  max: !isPlaceholder(CONTACTS.max),
}

// Пока данные не заменены, ссылки ведут к блоку контактов;
// после замены работают напрямую (tel:, mailto:, мессенджеры).
export const LINKS = {
  tel: CONFIGURED.phone ? `tel:${CONTACTS.phone.replace(/[^+\d]/g, '')}` : '#contacts',
  mail: CONFIGURED.email ? `mailto:${CONTACTS.email}` : '#contacts',
  whatsapp: CONFIGURED.whatsapp ? CONTACTS.whatsapp : '#contacts',
  max: CONFIGURED.max ? CONTACTS.max : '#contacts',
}

export const externalLinkProps = (configured: boolean) =>
  configured ? ({ target: '_blank', rel: 'noopener noreferrer' } as const) : {}
