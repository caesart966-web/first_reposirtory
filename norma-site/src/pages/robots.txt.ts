import type { APIRoute } from 'astro'

// robots.txt генерируется при сборке.
// На превью (NOINDEX=1) сайт полностью закрыт от поисковиков — черновик
// не должен попасть в выдачу. Боевая сборка открывает индексацию и указывает
// адрес карты сайта.
export const GET: APIRoute = ({ site }) => {
  const noindex = import.meta.env.PUBLIC_NOINDEX === '1'

  const body = noindex
    ? 'User-agent: *\nDisallow: /\n'
    : [
        'User-agent: *',
        'Allow: /',
        // Clean-param читает только Яндекс (Google строку пропускает).
        // Метки рекламы и рассылок (utm_*, yclid из Директа, gclid),
        // ysclid, который Яндекс дописывает к переходам из выдачи, и метки
        // старых счётчиков (_openstat, from) не меняют содержимое страницы.
        // Без этой строки каждый адрес с меткой Яндекс вправе считать
        // отдельной страницей, и в «Диагностике» Вебмастера они всплывают
        // дублями с GET-параметрами: с запуском Директа это сотни адресов.
        // Директива межсекционная — действует, где бы ни стояла.
        'Clean-param: utm_source&utm_medium&utm_campaign&utm_content&utm_term',
        'Clean-param: yclid&ysclid&gclid&_openstat&from',
        '',
        `Sitemap: ${new URL('sitemap-index.xml', site).toString()}`,
        '',
      ].join('\n')

  return new Response(body, { headers: { 'Content-Type': 'text/plain; charset=utf-8' } })
}
