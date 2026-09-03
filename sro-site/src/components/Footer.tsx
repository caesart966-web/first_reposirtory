import { Mail, Phone } from 'lucide-react'
import { CONFIGURED, CONTACTS, LINKS } from '../content/contacts'
import { REQUISITES } from '../content/facts'
import { SECTIONS } from '../content/nav'
import { ScalesMark } from './illustrations'
import { useLegalDocs } from './LegalDocs'
import { MESSENGERS } from './messengers'

export function Footer() {
  const openLegal = useLegalDocs()

  return (
    // id="contacts" — на подвале, а не на секции: отдельной секции контактов
    // больше нет, но якорь на неё ведёт из меню, из подвала и из запасных
    // ссылок в contacts.ts. Подвал и есть теперь место, где собраны все
    // способы связи, поэтому якорь указывает сюда, а не в никуда.
    <footer id="contacts" className="border-t border-neutral-200 bg-neutral-50/55">
      <div className="mx-auto w-full max-w-6xl px-4 py-12 sm:px-6 lg:px-8">
        {/* Правой части отдано больше ширины, чем раньше (2.4 против 1.9):
            ряду из трёх плашек мессенджеров нужно ~330px, иначе он ломается
            на две строки и «WhatsApp» висит один. */}
        <div className="grid gap-10 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,2.4fr)] lg:gap-16">
          <div>
            {/* Тот же знак, что в шапке: подвал — вторая точка, где страница
                называет себя, и называть себя дважды по-разному незачем. */}
            <div className="flex items-center gap-2.5">
              <ScalesMark className="h-[22px] w-auto shrink-0 text-accent-600" />
              <span className="flex flex-col leading-tight">
                <span className="font-bold text-neutral-950">{CONTACTS.brand}</span>
                {/* neutral-600, а не neutral-500 как в шапке: там подпись лежит
                    на белом, а здесь под ней ещё и фоновая гравюра Фемиды. Над
                    самой тёмной её точкой контраст neutral-500 падает до
                    4.39:1 при норме 4.5 — замерено на странице, а не по
                    заливке секции (по одной заливке вышло бы 4.62:1, и ошибку
                    было бы не видно). */}
                <span className="text-xs text-neutral-600">{CONTACTS.role}</span>
              </span>
            </div>
            <p className="mt-4 text-sm text-neutral-600">
              Вступление в СРО во всех регионах России: строительство, проектирование, инженерные
              изыскания.
            </p>
            {/* Формулировка «и первая, и все следующие» переехала сюда из
                убранной секции «Контакты». Она нигде больше на странице не
                повторяется дословно, а это условие заказчика — консультация
                бесплатна всегда, а не в первый разговор, — и оно обязано
                быть сказано прямо, а не подразумеваться. */}
            <p className="mt-3 text-sm font-medium text-accent-700">
              Консультация бесплатная — и первая, и все следующие
            </p>
          </div>

          {/* Заголовки колонок — той же капителью с разрядкой, что подзаголовки
              групп в «Услугах»: подвал перестаёт быть тремя случайными списками
              и читается частью той же системы. */}
          <div className="grid gap-9 sm:grid-cols-[minmax(0,0.7fr)_minmax(0,1.6fr)_minmax(0,1fr)] sm:gap-10">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-neutral-600">
                Разделы
              </p>
              {/* «Контакты» из списка выкинуты: якорь ведёт на сам подвал, и
                  внутри подвала это ссылка в никуда — щелчок ничего не
                  меняет. В шапке и в мобильном меню пункт остаётся: оттуда
                  он честно прокручивает страницу сюда. */}
              <ul className="mt-4 space-y-2.5 text-sm text-neutral-600">
                {SECTIONS.filter((section) => section.href !== '#contacts').map((section) => (
                  <li key={section.href}>
                    <a href={section.href} className="transition hover:text-accent-700">
                      {section.label}
                    </a>
                  </li>
                ))}
              </ul>
            </div>

            {/* Единственное место на странице, где собраны все способы связи:
                секция «Контакты» убрана — она была четвёртым по счёту призывом
                связаться (шапка, квиз, мобильная панель, она) и растаскивала
                внимание с квиза, который и есть точка конверсии.

                Три яруса сверху вниз — от самого прямого канала к самому
                отложенному: звонок, почта, мессенджеры. Мессенджеры — рядом
                плашек, а не списком: три одинаковых строки под почтой
                выглядели продолжением списка, а это выбор из равных.
                Подпись у каждой обязательна: значок без подписи опознаётся
                по силуэту, а MAX знаком далеко не всем.

                Всё внутри одного <ul>: у проверок это единый список каналов.
                Колонка целиком условная: заголовок над пустотой — та же
                ошибка, что была в «Контактах», и лечится так же. */}
            {(CONFIGURED.phone || CONFIGURED.email || MESSENGERS.length > 0) && (
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-neutral-600">
                  Связаться
                </p>
                <ul className="mt-4 space-y-3 text-sm text-neutral-600">
                  {CONFIGURED.phone && (
                    <li>
                      <a
                        href={LINKS.tel}
                        className="inline-flex items-center gap-2.5 transition hover:text-accent-700"
                      >
                        <Phone className="h-4 w-4 shrink-0 text-accent-600" aria-hidden="true" />
                        {/* Телефон крупнее и плотнее остальных строк: из всех
                            каналов он самый быстрый, и глаз должен находить его
                            первым, не читая колонку целиком. */}
                        <span className="text-lg font-semibold tracking-tight text-neutral-950">
                          {CONTACTS.phone}
                        </span>
                      </a>
                    </li>
                  )}
                  {CONFIGURED.email && (
                    <li>
                      <a
                        href={LINKS.mail}
                        className="inline-flex items-start gap-2.5 transition hover:text-accent-700"
                      >
                        <Mail
                          className="mt-0.5 h-4 w-4 shrink-0 text-accent-600"
                          aria-hidden="true"
                        />
                        <span className="min-w-0 break-all">{CONTACTS.email}</span>
                      </a>
                    </li>
                  )}
                  {MESSENGERS.length > 0 && (
                    <li className="flex flex-wrap gap-1.5 pt-1">
                      {MESSENGERS.map((channel) => (
                        <a
                          key={channel.label}
                          href={channel.href}
                          data-channel={channel.label}
                          className="inline-flex items-center gap-1.5 rounded-xl border border-neutral-200 bg-white px-2.5 py-2 text-sm font-medium text-neutral-700 transition hover:border-accent-400 hover:text-accent-700"
                        >
                          <channel.icon className="h-4 w-4 shrink-0 text-accent-600" />
                          {channel.label}
                        </a>
                      ))}
                    </li>
                  )}
                </ul>
              </div>
            )}

            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-neutral-600">
                Документы
              </p>
              <ul className="mt-4 space-y-2.5 text-sm text-neutral-600">
                {/* Открывают типовые тексты под 152-ФЗ; оператор назван реквизитами */}
                <li>
                  <button
                    type="button"
                    onClick={() => openLegal('privacy')}
                    className="text-left transition hover:text-accent-700"
                  >
                    Политика конфиденциальности
                  </button>
                </li>
                <li>
                  <button
                    type="button"
                    onClick={() => openLegal('consent')}
                    className="text-left transition hover:text-accent-700"
                  >
                    Согласие на обработку персональных данных
                  </button>
                </li>
              </ul>
            </div>
          </div>
        </div>

        <div className="mt-10 flex flex-col gap-2 border-t border-neutral-200 pt-6 text-sm text-neutral-600 sm:flex-row sm:items-center sm:justify-between">
          <p>
            {/* В копирайте — юридическое имя и ИНН, а не бренд: это то место
                на странице, где компания названа так, как в реестре. По ИНН
                её можно проверить в открытом реестре — для подвала это
                дешёвый и честный знак «мы настоящие». */}
            © {new Date().getFullYear()} {REQUISITES.legalName} · ИНН {REQUISITES.inn}
          </p>
          {/* Цен на странице нет, сроков тоже — оговорка про оферту это
              фиксирует, а не прикрывает. */}
          <p>Информация на сайте не является публичной офертой.</p>
        </div>
      </div>
    </footer>
  )
}
