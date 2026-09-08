import type { ReactNode } from 'react'
import { messengerHref, type MessengerKey } from '../content/contacts'
import { useDesktopPointer } from '../lib/useDesktopPointer'

// Ссылка на мессенджер: на телефоне — в той же вкладке, на компьютере — в новой.
//
// Телефон и планшет: обычный переход по универсальной ссылке (wa.me, t.me,
// max.ru). Только так iOS и Android открывают приложение; с target="_blank"
// вместо него открывалась пустая страница — заказчик поймал это на живом
// сайте, подробности в README.
//
// Компьютер: та же ссылка, но в новой вкладке — сайт остаётся открытым.
// Выбор «веб-версия или приложение» делает страница самого мессенджера:
// t.me предлагает «Open in Web» и «Open chat», wa.me — «Continue to chat»
// с переходом в WhatsApp Web или в программу, а браузер спрашивает, открыть
// ли приложение. Своего меню на сайте нет намеренно: был вариант с
// собственным выбором «веб / приложение» прямо на кнопке, заказчик его
// посмотрел и попросил именно привычный выбор на странице мессенджера.
//
// Устройство определяется по указателю, а не по ширине экрана: планшет в
// альбомной ориентации шире ноутбука, а приложения на нём открываются как
// на телефоне.
type Props = {
  channel: MessengerKey
  /** Имя канала на экране — оно же идёт в data-channel для проверок. */
  label: string
  /** Готовый текст сообщения; умеет принимать только WhatsApp. */
  text?: string
  className?: string
  children: ReactNode
}

export function MessengerLink({ channel, label, text, className = '', children }: Props) {
  const desktop = useDesktopPointer()
  return (
    <a
      href={messengerHref(channel, text)}
      className={className}
      data-channel={label}
      {...(desktop ? { target: '_blank', rel: 'noopener noreferrer' } : {})}
    >
      {children}
    </a>
  )
}
