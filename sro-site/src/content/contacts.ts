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
  // MAX. Личная ссылка профиля — расшифрована из QR-кода, который заказчик
  // выгрузил из приложения (аватар -> значок QR) и прислал 30.08.2026; ссылки
  // по номеру телефона у MAX не существует намеренно, номер собеседника там
  // не показывается нигде. Если заказчик пересоздаст QR в приложении, хеш
  // может смениться — тогда ссылку нужно обновить тем же путём.
  max: 'https://max.ru/u/f9LHodD0cOJH-7DT2fACPZwYLPwbc7t7KpCPXfuGhpg987BNumzPfeB0RNk',
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

// Ссылки мессенджеров открываются В ТОЙ ЖЕ вкладке, и это не упущение.
// Раньше на них стояли target="_blank" + rel="noopener noreferrer", и на
// телефоне они не открывали приложение: ни iOS, ни Chrome на Android не
// запускают universal link / app link, если переход идёт в новую вкладку —
// вместо приложения открывается пустая страница или веб-версия. Чтобы
// телефон переключился в WhatsApp, Telegram или MAX, ссылка обязана быть
// обычным переходом.
//
// На компьютере посетитель при этом уходит со страницы на веб-версию
// мессенджера, и возвращается кнопкой «Назад». Это осознанный размен:
// на лендинге цель — чтобы человек написал, а телефонов среди посетителей
// заведомо больше. Телефон и почта всегда работали так же, без новой вкладки.
//
// Если когда-нибудь вернёте target="_blank" — вернёте и эту поломку.
