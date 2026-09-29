// Условия СРО-партнёра для карточки — общие условия из fees.ts плюс его
// собственные отличия (partner.fees в partners.ts).
//
// Отличия хранятся отдельно специально: карточка не может молча разойтись
// с предложением на первом экране — строка с отличием получает пометку
// (other), и шаблон ставит у неё звёздочку.
//
// Отдельным модулем, а не внутри страницы, потому что карточки стоят в двух
// местах: на городских страницах и в общем списке /partnery/. Считать одно
// и то же дважды значило бы однажды посчитать по-разному.
//
// npm run facts пересчитывает эти строки САМ, независимо от этого модуля:
// проверка, которая берёт ответ у проверяемого кода, ничего не проверяет.

import { FEES, money } from '../config/fees'
import { partnerFeeKind, partnerKindWord, regDate, type Partner } from '../config/partners'

/**
 * good — значение-льгота (0 ₽, «не требуется»): в карточке оно зелёное,
 * как на первом экране. Цвет — только подсказка глазу: отличие от
 * предложения по-прежнему называет звёздочка, и красная пометка отличия
 * важнее зелёной (шаблон красит зелёным только строки без отличия).
 */
export type PartnerRow = { label: string; value: string; other: boolean; good: boolean }

export const partnerTerms = (p: Partner) => {
  const base = FEES[partnerFeeKind(p.reg)]
  const entry = p.fees?.entry ?? base.entry
  const member = p.fees?.memberMonth ?? base.memberMonth
  const target = p.fees?.target ?? base.target
  const insurance = p.insurance ?? 'не требуется в первый год'
  const rows: PartnerRow[] = [
    { label: 'Вступительный взнос', value: money(entry), other: entry !== base.entry, good: entry === 0 },
    { label: 'Членский взнос', value: `${money(member)} в месяц`, other: member !== base.memberMonth, good: member === 0 },
    { label: `Целевой взнос в ${base.union}`, value: money(target), other: target !== base.target, good: target === 0 },
    { label: 'Страхование', value: insurance, other: !!p.insurance, good: insurance.startsWith('не требуется') },
  ]
  return { p, kindWord: partnerKindWord(p.reg), since: regDate(p.reg), rows }
}

/** Отличаются ли условия хоть одной из этих СРО от предложения на первом экране. */
export const anyDiffers = (partners: readonly Partner[]) =>
  partners.some((p) => partnerTerms(p).rows.some((row) => row.other))
