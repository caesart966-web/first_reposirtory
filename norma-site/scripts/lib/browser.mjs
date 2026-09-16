// Браузер для проверок: тот же playwright, но с заранее сделанным выбором
// про файлы cookie.
//
// ЗАЧЕМ. Полоса про cookie (CookieBanner.astro) появляется на первом заходе
// и лежит у нижнего края экрана. Для посетителя это одно нажатие, а для
// проверок — накрытая часть страницы: клики по элементам под полосой
// перехватываются, а замер пикселей берёт её фон вместо фотографии.
// Ловилось это не всегда, а через раз, и выглядело как случайный сбой:
// «✗ Проверка не прошла: калькулятор взносов», при том что тот же скрипт
// по отдельности проходил.
//
// Поэтому контекст проверки открывается так, будто посетитель уже ответил.
// Ответ выбран «только необходимые» — тогда Метрика не грузится и проверки
// не стучатся к Яндексу.
//
// ЧЕГО ЗДЕСЬ НЕТ. Полоса не выключается насовсем: её саму меряет
// scripts/test-contrast.mjs, и он нарочно берёт настоящий playwright,
// а не эту обёртку — иначе единственная проверка полосы перестала бы
// её видеть.
import { chromium as playwright } from 'playwright'

/** Выполняется в браузере до загрузки страницы. */
const answerCookieNote = () => {
  try {
    localStorage.setItem('norma-cookie', 'need')
  } catch (e) {
    /* приватное окно: не сохранили — полоса просто появится */
  }
}

export const chromium = {
  async launch(options) {
    const browser = await playwright.launch(options)
    const newContext = browser.newContext.bind(browser)
    const newPage = browser.newPage.bind(browser)

    browser.newContext = async (opts) => {
      const ctx = await newContext(opts)
      await ctx.addInitScript(answerCookieNote)
      return ctx
    }
    browser.newPage = async (opts) => {
      const page = await newPage(opts)
      await page.addInitScript(answerCookieNote)
      return page
    }
    return browser
  },
}
