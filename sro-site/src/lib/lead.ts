export type Lead = {
  name: string
  phone: string
  email: string
  answers: Record<string, string>
}

// Текст заявки для отправки в мессенджер или на почту.
export function buildLeadMessage(lead: Lead): string {
  return [
    'Заявка с сайта',
    `Имя: ${lead.name}`,
    `Телефон: ${lead.phone}`,
    `E-mail: ${lead.email}`,
    ...Object.entries(lead.answers).map(([question, answer]) => `${question}: ${answer}`),
  ].join('\n')
}

// Точка интеграции формы. Сейчас заявка автоматически никуда не отправляется —
// посетителю предлагается отправить её в один клик через WhatsApp или e-mail
// (см. экран успеха в Quiz.tsx). Подключите сюда автоматический приём:
// backend, email-сервис, CRM или бота в мессенджере.
export async function sendLead(lead: Lead): Promise<void> {
  console.info('Новая заявка (подключите автоматическую отправку в src/lib/lead.ts):', lead)
}
