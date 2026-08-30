// Русское склонение после числа. Нужно там, где число подставляется из данных:
// «4 вопроса», но «5 вопросов» — жёстко зашитая форма молча соврёт, стоит
// добавить в квиз пятый вопрос. Ровно от такой тихой рассинхронизации уводили
// и ссылки на вопросы по имени вместо индекса.
export function plural(count: number, one: string, few: string, many: string): string {
  const mod10 = count % 10
  const mod100 = count % 100
  if (mod10 === 1 && mod100 !== 11) return one
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return few
  return many
}
