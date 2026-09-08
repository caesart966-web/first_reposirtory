// Навигация сайта в одном месте: её перечисляют шапка, мобильное меню и
// подвал, и расходиться эти списки не должны — переименованный раздел иначе
// живёт под двумя названиями, а удалённый оставляет ссылку в никуда.
//
// Два вида ссылок. anchor — секция главной страницы ('#services'); page —
// отдельная страница вида СРО ('sro-stroiteley'), у неё свой адрес и на
// главной её нет. Разница важна для helpers из lib/site.ts: с вложенной
// страницы якорь надо предварять '../', а адрес страницы — собирать целиком.
import { anchor, page } from '../lib/site'
import { SERVICE_PAGES } from './services'
import { SRO_DETAILS } from './sroDetails'

export type NavLink = {
  label: string
  /** Якорь секции главной либо папка страницы — см. kind. */
  href: string
  kind: 'anchor' | 'page'
  /** Не показывать в шапке: место там ограничено, а раздел второстепенный. */
  footerOnly?: boolean
  /** Строка под названием в выпадающем меню. Только факты, уже проверенные
   *  на странице вида: сюда ничего не пишется руками. */
  hint?: string
}

export type NavGroup = {
  label: string
  items: NavLink[]
}

export type NavItem = NavLink | NavGroup

export const isGroup = (item: NavItem): item is NavGroup => 'items' in item

// Строка-подсказка под видом СРО в меню. Слова — из области деятельности
// на странице вида (scope), но не сам список: у изыскателей пять пунктов,
// каждый начинается с «инженерно-» и кончается на «изыскания», и целиком
// они занимали четыре строки в меню. Набор regions.mjs/header.mjs сверяет,
// что каждое слово подсказки есть на странице вида — подсказка не может
// уйти от того, что там написано.
const HINTS: Record<string, string> = {
  construction: 'Строительство, реконструкция, капитальный ремонт, снос',
  design: 'Архитектурно-строительное проектирование, проектная документация',
  survey: 'Инженерные изыскания: геодезические, геологические, экологические и другие',
}

/** Три страницы видов СРО — одно выпадающее меню. */
export const TYPES_GROUP: NavGroup = {
  label: 'Виды СРО',
  items: SRO_DETAILS.map((detail) => ({
    label: detail.card.title,
    href: detail.path,
    kind: 'page',
    hint: HINTS[detail.slug] ?? detail.scope.slice(0, 3).join(', '),
  })),
}

/** Что делаем — семь страниц услуг под /uslugi/. */
export const SERVICES_GROUP: NavGroup = {
  label: 'Услуги',
  items: SERVICE_PAGES.map((service) => ({
    label: service.short,
    href: service.path,
    kind: 'page',
    hint: service.hint,
  })),
}

// Порядок — как разделы идут на странице. В шапке на 1024-1279px места
// ровно на эти пункты плюс телефон и кнопка; в мобильном меню и в подвале
// ограничения нет, там раскрыты и группы.
export const MENU: NavItem[] = [
  TYPES_GROUP,
  SERVICES_GROUP,
  { label: 'Стоимость', href: '#pricing', kind: 'anchor' },
  { label: 'О нас', href: '#about', kind: 'anchor' },
  { label: 'FAQ', href: '#faq', kind: 'anchor' },
  // География — в подвале и мобильном меню; в шапке для неё нет места,
  // а из «Услуг» она ушла, когда там появились страницы услуг.
  { label: 'География работы', href: '#regions', kind: 'anchor', footerOnly: true },
  // Ведёт в подвал: отдельной секции контактов нет, все каналы собраны там.
  // В шапке не показывается — там телефон и кнопка заявки и так стоят рядом.
  { label: 'Контакты', href: '#contacts', kind: 'anchor' },
]

export const HEADER_NAV = MENU.filter((item) => isGroup(item) || (item.href !== '#contacts' && !item.footerOnly))

/** Плоский список для подвала: группы раскрыты, страницы видов идут
 *  первыми, как и на самой странице. */
export const SECTIONS: NavLink[] = MENU.flatMap((item) => (isGroup(item) ? item.items : [item]))

/** Адрес ссылки с учётом её вида: якорь главной или страница вида СРО.
 *  Вынесено сюда, а не в lib/site.ts: там нет знания о форме навигации. */
export const navHref = (link: NavLink) => (link.kind === 'page' ? page(link.href) : anchor(link.href))
