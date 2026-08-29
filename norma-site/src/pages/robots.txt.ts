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
        '',
        `Sitemap: ${new URL('sitemap-index.xml', site).toString()}`,
        '',
      ].join('\n')

  return new Response(body, { headers: { 'Content-Type': 'text/plain; charset=utf-8' } })
}
