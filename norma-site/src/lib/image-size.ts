import { readFileSync } from 'node:fs'

// Размер картинки из заголовка файла — для width и height у <img>:
// браузер узнаёт пропорцию до загрузки, а check-html не пишет замечание.
// Читаются только WebP и PNG — других форматов в public/img нет.
// Для чужого формата вернётся null, и атрибутов просто не будет.
export function imageSize(path: string): { width: number; height: number } | null {
  const b = readFileSync(path)
  if (b.toString('ascii', 0, 4) === 'RIFF' && b.toString('ascii', 8, 12) === 'WEBP') {
    const chunk = b.toString('ascii', 12, 16)
    if (chunk === 'VP8X') return { width: 1 + b.readUIntLE(24, 3), height: 1 + b.readUIntLE(27, 3) }
    if (chunk === 'VP8 ') return { width: b.readUInt16LE(26) & 0x3fff, height: b.readUInt16LE(28) & 0x3fff }
    if (chunk === 'VP8L') {
      const n = b.readUInt32LE(21)
      return { width: 1 + (n & 0x3fff), height: 1 + ((n >> 14) & 0x3fff) }
    }
  }
  if (b.length > 24 && b.readUInt32BE(0) === 0x89504e47) return { width: b.readUInt32BE(16), height: b.readUInt32BE(20) }
  return null
}
