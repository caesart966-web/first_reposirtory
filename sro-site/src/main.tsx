import '@fontsource-variable/onest'
import '@fontsource-variable/brygada-1918'
import './index.css'
import App from './App'
import { markArrival } from './lib/arrival'
import { setSiteRoot } from './lib/site'
import { start } from './lib/start'

// Главная лежит в корне: префикса до корня у неё нет.
// Пришли со своей страницы — без вступления (lib/arrival.ts).
markArrival()

setSiteRoot('')

// Готовая разметка видна сразу, скрипт её подхватывает (lib/start.tsx).
// До 20.10.2026 первая отрисовка шла синхронно (flushSync), а скрипт
// блокировал показ страницы (blocking="render"): без готовой разметки
// плавный переход между страницами снимал бы пустой лист. Готовая разметка
// есть с 15.10.2026, и ждать скрипт больше незачем.
start(document.getElementById('root')!, <App />)
