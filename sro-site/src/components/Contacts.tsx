import { Mail, Phone } from "lucide-react";
import {
  CONFIGURED,
  CONTACTS,
  LINKS,
  externalLinkProps,
} from "../content/contacts";
import { MaxIcon, TelegramIcon, WhatsAppIcon } from "./icons";
import { Reveal } from "./ui/Reveal";
import { Section, SectionHeading } from "./ui/Section";

// Канал попадает в список только когда для него настроена рабочая ссылка.
const MESSENGERS = [
  ...(CONFIGURED.whatsapp
    ? [
        {
          label: "WhatsApp",
          hint: CONTACTS.phone,
          href: LINKS.whatsapp,
          icon: WhatsAppIcon,
        },
      ]
    : []),
  ...(CONFIGURED.telegram
    ? [
        {
          label: "Telegram",
          hint: "Написать в чат",
          href: LINKS.telegram,
          icon: TelegramIcon,
        },
      ]
    : []),
  ...(CONFIGURED.max
    ? [{ label: "MAX", hint: "Написать в чат", href: LINKS.max, icon: MaxIcon }]
    : []),
];

export function Contacts() {
  return (
    <Section id="contacts">
      <SectionHeading
        eyebrow="Контакты"
        title="Свяжитесь удобным способом"
        subtitle="Телефон, почта или мессенджеры — как вам удобнее. Первый разговор — бесплатный."
      />
      {/* Вся секция — одна панель-визитка (rounded-3xl, как у панелей этого
          масштаба: карточка героя, квиз, «Что войдёт в пакет»). Колонки делит
          тонкий фирменный разделитель, а не пустой отступ: раньше два столбца
          текста «парили» в воздухе. На мобильном разделитель горизонтальный.
          Внутри — только линии между строками: рамка в рамке тяжелит.
          Иконки слева и справа одного размера и цвета: без левых колонка
          «Позвонить или написать» читалась как другой блок. */}
      <Reveal className="mx-auto mt-10 max-w-4xl">
        <div className="grid rounded-3xl border border-neutral-200 bg-white p-6 shadow-card sm:p-10 lg:grid-cols-[1fr_auto_1fr] lg:gap-10">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.16em] text-neutral-600">
              Позвонить или написать
            </p>
            <div className="mt-4 divide-y divide-neutral-200">
              <a
                href={LINKS.tel}
                className="flex items-center gap-4 py-4 transition-colors duration-200 hover:bg-accent-50/40"
              >
                <Phone
                  className="h-5 w-5 shrink-0 text-accent-600"
                  aria-hidden="true"
                />
                <span className="text-2xl font-bold tracking-tight text-neutral-950 sm:text-3xl">
                  {CONTACTS.phone}
                </span>
              </a>
              <a
                href={LINKS.mail}
                className="flex items-center gap-4 py-4 transition-colors duration-200 hover:bg-accent-50/40"
              >
                <Mail
                  className="h-5 w-5 shrink-0 text-accent-600"
                  aria-hidden="true"
                />
                {/* break-all: без него длинный адрес рядом с иконкой вылезал
                    за карточку на узких экранах. */}
                <span className="min-w-0 break-all text-lg text-neutral-700">
                  {CONTACTS.email}
                </span>
              </a>
            </div>
          </div>

          <div
            className="my-8 h-px w-full bg-accent-200 lg:my-0 lg:h-auto lg:w-0.5 lg:self-stretch"
            aria-hidden="true"
          />

          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.16em] text-neutral-600">
              Мессенджеры
            </p>
            <div className="mt-4 divide-y divide-neutral-200">
              {MESSENGERS.map((channel) => (
                <a
                  key={channel.label}
                  href={channel.href}
                  {...externalLinkProps(true)}
                  className="group flex items-center gap-4 py-4 transition-colors duration-200 hover:bg-accent-50/40"
                >
                  <channel.icon className="h-5 w-5 shrink-0 text-accent-600" />
                  <span className="min-w-0 flex-1">
                    <span className="block font-medium text-neutral-950">
                      {channel.label}
                    </span>
                    <span className="block text-sm text-neutral-600">
                      {channel.hint}
                    </span>
                  </span>
                </a>
              ))}
            </div>
          </div>
        </div>
      </Reveal>
    </Section>
  );
}
