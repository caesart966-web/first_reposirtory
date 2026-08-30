// Единая точка правды для контактов сайта.
export const CONTACTS = {
  name: 'Игорь Парфенов',
  fullName: 'Парфенов Игорь Владимирович',
  role: 'Эксперт по СРО',
  phone: '+7 900 133-02-19',
  email: '9001330219@mail.ru',
  whatsapp: 'https://wa.me/79001330219',
  // Публичная ссылка по номеру. Если появится @username — замените на https://t.me/username
  telegram: 'https://t.me/+79001330219',
  // MAX. Ссылки по номеру телефона у него нет и не предвидится: в отличие от
  // WhatsApp (wa.me/номер) там это закрыто намеренно, из соображений
  // приватности — номер собеседника в MAX вообще нигде не показывается.
  // Поиск по номеру работает только внутри приложения, ссылкой с сайта его
  // не заменить.
  //
  // Рабочая ссылка одна — личная, вида https://max.ru/u/<длинный хеш>. Берётся
  // в приложении: аватар в левом верхнем углу -> значок QR рядом с именем ->
  // «Скопировать ссылку» / «Поделиться». Подставьте её сюда — кнопки MAX
  // появятся в подвале и в мобильной панели сами.
  max: '[MAX_LINK]',
} as const

const isPlaceholder = (value: string) => value.startsWith('[') && value.endsWith(']')

export const CONFIGURED = {
  phone: !isPlaceholder(CONTACTS.phone),
  email: !isPlaceholder(CONTACTS.email),
  whatsapp: !isPlaceholder(CONTACTS.whatsapp),
  telegram: !isPlaceholder(CONTACTS.telegram),
  max: !isPlaceholder(CONTACTS.max),
}

// Пока значение не заменено, ссылка ведёт к подвалу — там собраны все каналы.
export const LINKS = {
  tel: CONFIGURED.phone ? `tel:${CONTACTS.phone.replace(/[^+\d]/g, '')}` : '#contacts',
  mail: CONFIGURED.email ? `mailto:${CONTACTS.email}` : '#contacts',
  whatsapp: CONFIGURED.whatsapp ? CONTACTS.whatsapp : '#contacts',
  telegram: CONFIGURED.telegram ? CONTACTS.telegram : '#contacts',
  max: CONFIGURED.max ? CONTACTS.max : '#contacts',
}

export const externalLinkProps = (configured: boolean) =>
  configured ? ({ target: '_blank', rel: 'noopener noreferrer' } as const) : {}
