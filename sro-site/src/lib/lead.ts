export type Lead = {
  name: string
  phone: string
  email: string
  answers: Record<string, string>
}

// Куда уходит заявка. Значения берутся из переменных окружения, чтобы сменить
// сервис приёма можно было без правки кода (например, при переезде на свой
// домен и российский хостинг — тогда меняется только VITE_LEAD_ENDPOINT).
//
// Ключ в коде не хранится: локально он берётся из .env (файл в .gitignore),
// на сборке — из секретов репозитория. Без ключа отправка не работает и
// посетитель видит экран ошибки с прямыми контактами — это лучше, чем
// молчаливая потеря заявок.
//
// Именно `||`, а не `??`: незаданный секрет в CI приходит пустой строкой,
// и её тоже нужно считать «значение не задано».
const ENDPOINT = import.meta.env.VITE_LEAD_ENDPOINT || 'https://api.web3forms.com/submit'
const ACCESS_KEY = import.meta.env.VITE_LEAD_ACCESS_KEY || ''

// Дольше ждать нет смысла: посетитель решит, что кнопка сломана.
const TIMEOUT_MS = 10_000

// Текст заявки: уходит в письмо и подставляется в сообщение мессенджера,
// если посетитель захочет продублировать заявку сам.
export function buildLeadMessage(lead: Lead): string {
  return [
    'Заявка с сайта',
    `Имя: ${lead.name}`,
    `Телефон: ${lead.phone}`,
    ...(lead.email ? [`E-mail: ${lead.email}`] : []),
    ...Object.entries(lead.answers).map(([question, answer]) => `${question}: ${answer}`),
  ].join('\n')
}

// Отправляет заявку на почту через сервис приёма форм.
// Бросает ошибку в любом случае, когда доставка не подтверждена: молчаливого
// «успеха» быть не должно — иначе посетитель уверен, что заявка ушла, а её нет.
export async function sendLead(lead: Lead): Promise<void> {
  if (!ENDPOINT || !ACCESS_KEY) {
    throw new Error('Не настроен приём заявок: задайте VITE_LEAD_ENDPOINT и VITE_LEAD_ACCESS_KEY')
  }

  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), TIMEOUT_MS)

  try {
    const response = await fetch(ENDPOINT, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      signal: controller.signal,
      body: JSON.stringify({
        access_key: ACCESS_KEY,
        // Телефон в теме письма — чтобы перезванивать прямо из списка писем.
        subject: `Заявка с сайта СРО — ${lead.name}, ${lead.phone}`,
        from_name: lead.name,
        // Кнопка «Ответить» в почте должна отвечать клиенту, а не сервису.
        ...(lead.email ? { replyto: lead.email } : {}),
        message: buildLeadMessage(lead),
      }),
    })

    if (!response.ok) {
      throw new Error(`Сервис приёма заявок ответил ${response.status}`)
    }

    // Приёмник отвечает 200 и в случае отказа, поэтому проверяем тело ответа.
    //
    // Тело, которое не разбирается в JSON, — тоже отказ, а не успех. Так
    // выглядит чужая страница на месте приёмника: заглушка хостинга, HTML
    // с ошибкой или исходник PHP там, где PHP не выполняется. Раньше такой
    // ответ проходил как успешный, и заявка исчезала бесследно: посетитель
    // видел «Заявка отправлена», а письма не было. Лишний экран ошибки
    // с прямыми контактами дешевле потерянной заявки.
    const result = (await response.json().catch(() => null)) as { success?: boolean } | null
    if (!result || result.success === false) {
      throw new Error('Сервис приёма заявок не подтвердил доставку')
    }
  } finally {
    clearTimeout(timeout)
  }
}
