/* =========================================================================
   Обработчик заявок для Cloudflare Workers (бесплатного тарифа хватает).
   Принимает заявку с сайта и пересылает её в Telegram.

   Зачем: токен бота остаётся здесь, на стороне сервера, и в код сайта
   не попадает. Сайт при этом остаётся полностью статическим.

   Установка — пошагово в README, раздел «Заявки в Telegram», вариант А.
   Секреты задаются в Cloudflare, а не в этом файле:
     BOT_TOKEN   — токен бота от @BotFather
     CHAT_ID     — куда слать заявки
     ALLOW_ORIGIN — адрес сайта, например https://example.com
   ========================================================================= */

export default {
  async fetch(request, env) {
    const allow = env.ALLOW_ORIGIN || '*';
    const cors = {
      'Access-Control-Allow-Origin': allow,
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type'
    };

    if (request.method === 'OPTIONS') return new Response(null, { status: 204, headers: cors });
    if (request.method !== 'POST') return new Response('Method Not Allowed', { status: 405, headers: cors });

    // Принимаем заявки только со своего сайта
    const origin = request.headers.get('Origin') || '';
    if (allow !== '*' && origin && origin !== allow) {
      return new Response('Forbidden', { status: 403, headers: cors });
    }

    let data;
    try {
      data = await request.json();
    } catch {
      return new Response('Bad Request', { status: 400, headers: cors });
    }

    const clean = (v, max) => String(v ?? '').replace(/[<>]/g, '').trim().slice(0, max);
    const name = clean(data.name, 100);
    const phone = clean(data.phone, 40);

    if (!name || phone.replace(/\D/g, '').length < 10) {
      return new Response('Invalid', { status: 422, headers: cors });
    }

    const lines = [
      'Заявка с сайта',
      '',
      'Имя: ' + name,
      'Телефон: ' + phone
    ];
    if (data.service) lines.push('Услуга / объект: ' + clean(data.service, 200));
    if (data.comment) lines.push('Комментарий: ' + clean(data.comment, 2000));
    lines.push('', 'Страница: ' + clean(data.page, 300));

    const tg = await fetch(`https://api.telegram.org/bot${env.BOT_TOKEN}/sendMessage`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        chat_id: env.CHAT_ID,
        text: lines.join('\n'),
        disable_web_page_preview: true
      })
    });

    if (!tg.ok) return new Response('Upstream error', { status: 502, headers: cors });

    return new Response(JSON.stringify({ ok: true }), {
      status: 200,
      headers: { ...cors, 'Content-Type': 'application/json' }
    });
  }
};
