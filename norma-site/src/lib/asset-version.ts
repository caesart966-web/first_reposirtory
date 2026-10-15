import { createHash } from 'node:crypto'
import { readFileSync } from 'node:fs'

// Метка версии к адресу файла из public/: «/favicon.svg?v=1a2b3c4d».
//
// Зачем. Значки и превью лежат под постоянными именами, а браузер держит
// значок вкладки в своём кеше неделями — и .htaccess сам разрешает
// картинкам месяц. После перекраски в синий (07.10.2026) заказчик залил
// архив и увидел во вкладке прежний красный значок: файл на хостинге был
// новый, а браузер его не спрашивал. С меткой адрес меняется вместе
// с содержимым файла — и только тогда: пока файл тот же, кеш работает.
// Метка — первые 8 знаков SHA-1 содержимого, считается при сборке.

const memo = new Map<string, string>()

export function withVersion(path: string): string {
  let v = memo.get(path)
  if (!v) {
    v = createHash('sha1').update(readFileSync(`public${path}`)).digest('hex').slice(0, 8)
    memo.set(path, v)
  }
  return `${path}?v=${v}`
}
