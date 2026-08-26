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
