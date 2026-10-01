/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Куда отправлять заявку из квиза. По умолчанию — Web3Forms. */
  readonly VITE_LEAD_ENDPOINT?: string
  /** Ключ доступа сервиса приёма заявок. */
  readonly VITE_LEAD_ACCESS_KEY?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

/** Отпечатки картинок из public/img: 'img/hero-day.webp' → 'a1b2c3d4' (vite.config.ts). */
declare const __ASSET_VERSIONS__: Record<string, string>
