/* =========================================================================
   Скрипты сайта. Один файл на весь сайт, без библиотек.
   0. Шапка, появление блоков при прокрутке, счётчик цифр
   1. Мобильное меню
   2. Фоновое видео (грузится только там, где нужно)
   3. Всплывающее окно с документом
   4. Форма заявки -> Telegram
   ========================================================================= */
(function () {
  'use strict';

  var CFG = window.SITE_CONFIG || {};

  // Метка «скрипты работают». Всё, что прячет контент до анимации, висит
  // на этом классе — значит без JS и у поисковиков текст виден всегда.
  document.documentElement.classList.add('js');

  var calmMedia = window.matchMedia('(prefers-reduced-motion: reduce)');

  /* ---------- 0. Шапка: тень появляется только при прокрутке ------------- */
  var header = document.querySelector('.header');
  if (header) {
    var onScroll = function () {
      header.classList.toggle('is-scrolled', window.scrollY > 8);
    };
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
  }

  /* ---------- 0б. Появление блоков при прокрутке -------------------------
     Блоки чуть поднимаются, когда доходят до экрана. Приём известен своими
     болячками (пропавший текст в PDF, на якорях, при ошибке скрипта),
     поэтому обвязан страховками:
       • прячет блоки только этот код — класс can-reveal ставится ниже;
         не выполнился скрипт — страница видна целиком и сразу;
       • при системной настройке «уменьшить движение» ничего не прячется;
       • через 2,5 секунды после загрузки показывается всё оставшееся,
         даже если наблюдатель почему-то не сработал;
       • первый экран не трогаем — он появляется своей анимацией в CSS. */
  var revealTargets = [];
  if (!calmMedia.matches && 'IntersectionObserver' in window) {
    revealTargets = [].slice.call(document.querySelectorAll(
      '.section__head, .card, .object, .step, .rec, .service-list,' +
      ' .panel, .media-band, .faq, .form-card, .contact-card, .doc-list'
    )).filter(function (el) { return !el.closest('.hero'); });

    if (revealTargets.length) {
      document.documentElement.classList.add('can-reveal');
      revealTargets.forEach(function (el) { el.classList.add('reveal'); });

      var showAll = function () {
        revealTargets.forEach(function (el) { el.classList.add('is-in'); });
      };
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (e) {
          if (!e.isIntersecting) return;
          // Небольшая задержка по порядку внутри одного ряда: соседние
          // карточки появляются друг за другом, а не все разом.
          var sibs = e.target.parentNode ? e.target.parentNode.children : [];
          var i = [].indexOf.call(sibs, e.target);
          e.target.style.transitionDelay = (Math.min(i, 5) * 60) + 'ms';
          e.target.classList.add('is-in');
          io.unobserve(e.target);
        });
      }, { rootMargin: '0px 0px -8% 0px', threshold: 0.01 });

      revealTargets.forEach(function (el) { io.observe(el); });
      // Страховка: что бы ни случилось, невидимого текста не остаётся.
      window.setTimeout(showAll, 2500);
      window.addEventListener('beforeprint', showAll);
    }
  }

  /* ---------- 0в. Счётчик цифр первого экрана ---------------------------
     Значения уже стоят в разметке — скрипт только «прокручивает» их от нуля.
     Если скрипта нет или движение выключено, цифры просто стоят на месте. */
  if (!calmMedia.matches) {
    [].forEach.call(document.querySelectorAll('.hero__spec-value'), function (el, n) {
      var target = parseInt(el.textContent, 10);
      if (!target || target > 999 || !el.firstChild) return;
      var started = 0;
      var step = function (now) {
        if (!started) started = now;
        var k = Math.min(1, (now - started) / 900);
        // Замедление к концу: цифра «доезжает», а не обрывается.
        var value = Math.round(target * (1 - Math.pow(1 - k, 3)));
        el.firstChild.nodeValue = String(value);
        if (k < 1) requestAnimationFrame(step);
      };
      el.firstChild.nodeValue = '0';
      window.setTimeout(function () { requestAnimationFrame(step); }, 320 + n * 90);
    });
  }

  /* ---------- 0г. Подсветка карточки за курсором -------------------------
     Скрипт только сообщает CSS координаты указателя внутри карточки,
     рисует всё стилями. На тач-экранах не включается: там наведения нет,
     и лишние обработчики ни к чему. */
  if (window.matchMedia('(hover: hover) and (pointer: fine)').matches) {
    var spotCards = document.querySelectorAll('.service-item, .section--dark .card');
    Array.prototype.forEach.call(spotCards, function (card) {
      card.addEventListener('pointermove', function (e) {
        var r = card.getBoundingClientRect();
        card.style.setProperty('--mx', (e.clientX - r.left) + 'px');
        card.style.setProperty('--my', (e.clientY - r.top) + 'px');
      });
    });
  }

  /* ---------- 1. Мобильное меню ----------------------------------------- */
  var burger = document.querySelector('.burger');
  var nav = document.getElementById('nav');
  if (burger && nav) {
    burger.addEventListener('click', function () {
      var open = nav.classList.toggle('is-open');
      burger.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
    nav.addEventListener('click', function (e) {
      if (e.target.closest('a')) {
        nav.classList.remove('is-open');
        burger.setAttribute('aria-expanded', 'false');
      }
    });
  }

  /* ---------- 2. Фоновое видео ------------------------------------------
     Видео играет на всех экранах, включая телефоны, — решение заказчика.
     Кадр вместо видео остаётся в двух случаях: включена экономия трафика
     или в системе отключены анимации. Источники подставляются скриптом
     после полной загрузки страницы, чтобы первый экран ничего не ждал.  */
  var videos = document.querySelectorAll('.js-video');
  if (videos.length) {
    var calm = calmMedia.matches;
    var saveData = navigator.connection && navigator.connection.saveData;

    Array.prototype.forEach.call(videos, function (video) {
      if (calm || saveData) { video.remove(); return; }

      var start = function () {
        // На узких экранах берём облегчённый файл, если он подготовлен:
        // 400 КБ вместо 1,2 МБ на мобильном интернете заметны сразу.
        var narrow = window.matchMedia('(max-width: 43.6875em)').matches;
        var list = (narrow && video.getAttribute('data-src-mobile')) ||
                   video.getAttribute('data-src') || '';
        list.split('|').forEach(function (src) {
          if (!src) return;
          var s = document.createElement('source');
          s.src = src;
          s.type = src.indexOf('.webm') > -1 ? 'video/webm' : 'video/mp4';
          video.appendChild(s);
        });
        video.load();
        var p = video.play();
        // Если автозапуск запрещён — просто остаётся постер, ошибку гасим.
        if (p && p.catch) p.catch(function () { video.remove(); });
      };
      // Ждём полной загрузки страницы: видео не задерживает отрисовку.
      if (document.readyState === 'complete') start();
      else window.addEventListener('load', start);
    });
  }

  /* ---------- 3. Всплывающее окно с документом ---------------------------
     Письма и благодарности показываются картинкой прямо на сайте, а не
     открываются PDF-файлом в новой вкладке. Ссылка на исходный PDF есть
     внутри окна — тому, кому нужен сам документ.
     Картинка грузится только в момент открытия, страница от неё не тяжелеет. */
  var lightbox = null;
  var lastFocused = null;
  var items = [];          // список картинок текущего просмотра
  var current = 0;         // какая показана
  var baseCaption = '';

  function buildLightbox() {
    var el = document.createElement('div');
    el.className = 'lightbox';
    el.setAttribute('role', 'dialog');
    el.setAttribute('aria-modal', 'true');
    el.setAttribute('aria-label', 'Просмотр документа');
    el.hidden = true;
    var arrow = function (dir) {
      return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" ' +
             'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
             (dir === 'prev' ? '<path d="M15 5 8 12l7 7"/>' : '<path d="M9 5l7 7-7 7"/>') + '</svg>';
    };
    el.innerHTML =
      '<div class="lightbox__inner">' +
        '<div class="lightbox__bar">' +
          '<span class="lightbox__caption"></span>' +
          '<span class="lightbox__actions">' +
            '<a class="lightbox__btn" data-pdf-link hidden target="_blank" rel="noopener">Скачать PDF</a>' +
            '<button class="lightbox__btn" type="button" data-close aria-label="Закрыть">Закрыть</button>' +
          '</span>' +
        '</div>' +
        '<button class="lightbox__nav lightbox__nav--prev" type="button" data-prev aria-label="Предыдущее фото" hidden>' + arrow('prev') + '</button>' +
        '<button class="lightbox__nav lightbox__nav--next" type="button" data-next aria-label="Следующее фото" hidden>' + arrow('next') + '</button>' +
        '<div class="lightbox__scroll"><img class="lightbox__img" alt=""></div>' +
      '</div>';
    document.body.appendChild(el);

    // Закрытие: крестик, клик по тёмному фону, Esc
    el.addEventListener('click', function (e) {
      if (e.target === el || e.target.closest('[data-close]')) { closeLightbox(); return; }
      if (e.target.closest('[data-prev]')) show(current - 1);
      if (e.target.closest('[data-next]')) show(current + 1);
    });
    return el;
  }

  // Показывает кадр по номеру. Список из одной картинки — обычный просмотр,
  // из нескольких — галерея со стрелками.
  function show(index) {
    if (!items.length) return;
    current = (index + items.length) % items.length;   // по кругу
    var img = lightbox.querySelector('.lightbox__img');
    img.src = items[current];
    img.alt = baseCaption || 'Изображение';
    var many = items.length > 1;
    lightbox.querySelector('[data-prev]').hidden = !many;
    lightbox.querySelector('[data-next]').hidden = !many;
    lightbox.querySelector('.lightbox__caption').textContent =
      baseCaption + (many ? '  ·  ' + (current + 1) + ' / ' + items.length : '');
    lightbox.querySelector('.lightbox__scroll').scrollTop = 0;
  }

  function openLightbox(trigger) {
    if (!lightbox) lightbox = buildLightbox();
    lastFocused = trigger;
    baseCaption = trigger.getAttribute('data-caption') || '';

    var gallery = trigger.getAttribute('data-gallery');
    if (gallery) {
      try { items = JSON.parse(gallery); }
      catch (e) { items = []; }
    } else {
      items = [trigger.getAttribute('data-lightbox')];
    }

    var pdf = lightbox.querySelector('[data-pdf-link]');
    var pdfHref = trigger.getAttribute('data-pdf');
    if (pdfHref) { pdf.href = pdfHref; pdf.hidden = false; }
    else { pdf.removeAttribute('href'); pdf.hidden = true; }

    show(0);
    lightbox.hidden = false;
    document.body.classList.add('is-locked');
    lightbox.querySelector('[data-close]').focus();
  }

  function closeLightbox() {
    if (!lightbox || lightbox.hidden) return;
    lightbox.hidden = true;
    lightbox.querySelector('.lightbox__img').removeAttribute('src');
    document.body.classList.remove('is-locked');
    if (lastFocused) { lastFocused.focus(); lastFocused = null; }
  }

  document.addEventListener('click', function (e) {
    var trigger = e.target.closest('[data-lightbox], [data-gallery]');
    if (!trigger) return;
    e.preventDefault();
    openLightbox(trigger);
  });

  document.addEventListener('keydown', function (e) {
    if (!lightbox || lightbox.hidden) return;
    if (e.key === 'Escape') closeLightbox();
    if (e.key === 'ArrowLeft') show(current - 1);
    if (e.key === 'ArrowRight') show(current + 1);
  });

  /* ---------- 4. Форма заявки -------------------------------------------- */
  var forms = document.querySelectorAll('form[data-form="lead"]');

  function digits(s) { return (s || '').replace(/\D/g, ''); }

  function setError(field, message) {
    var wrap = field.closest('.field');
    if (!wrap) return;
    wrap.classList.toggle('is-error', !!message);
    wrap.classList.toggle('field--error', !!message);
    var box = wrap.querySelector('.field__error');
    if (box) box.textContent = message || '';
  }

  function validate(form) {
    var ok = true;
    var name = form.elements.name;
    var phone = form.elements.phone;

    if (!name.value.trim()) { setError(name, 'Укажите, как к вам обращаться'); ok = false; }
    else setError(name, '');

    var d = digits(phone.value);
    if (d.length < 10) { setError(phone, 'Укажите телефон — 10 цифр и больше'); ok = false; }
    else setError(phone, '');

    return ok;
  }

  function buildMessage(form) {
    var f = form.elements;
    var lines = [
      'Заявка с сайта',
      '',
      'Имя: ' + f.name.value.trim(),
      'Телефон: ' + f.phone.value.trim()
    ];
    if (f.service && f.service.value) lines.push('Услуга / объект: ' + f.service.value);
    if (f.comment && f.comment.value.trim()) lines.push('Комментарий: ' + f.comment.value.trim());
    lines.push('');
    lines.push('Страница: ' + window.location.href);
    return lines.join('\n');
  }

  function showStatus(form, kind, text) {
    var box = form.querySelector('.form__status');
    if (!box) return;
    box.className = 'form__status form__status--' + kind;
    box.textContent = text;
  }

  /* Отправка не прошла — заявка не должна пропасть.
     Показываем три запасных пути, и в письме уже подставлено всё, что человек
     написал: ему остаётся нажать «отправить» в своей почте. Причины бывают
     разные — не настроен приём заявок, нет связи, заблокирован запрос. */
  function showRescue(form) {
    var box = form.querySelector('.form__status');
    if (!box) return;
    var mail = form.getAttribute('data-mail');
    var tel = form.getAttribute('data-tel');
    var telText = form.getAttribute('data-tel-display') || tel;
    var tg = form.getAttribute('data-tg');
    var row = document.createElement('div');
    row.className = 'form__rescue';

    if (tel) {
      row.appendChild(link('tel:' + tel, 'Позвонить ' + telText, 'btn--primary'));
    }
    if (mail) {
      var href = 'mailto:' + mail +
        '?subject=' + encodeURIComponent('Заявка с сайта') +
        '&body=' + encodeURIComponent(buildMessage(form));
      row.appendChild(link(href, 'Отправить письмом', 'btn--ghost'));
    }
    if (tg) {
      var a = link(tg, 'Написать в Telegram', 'btn--ghost');
      a.rel = 'nofollow noopener';
      row.appendChild(a);
    }
    box.appendChild(row);

    function link(href, text, kind) {
      var a = document.createElement('a');
      a.className = 'btn ' + kind + ' btn--sm';
      a.href = href;
      a.textContent = text;
      return a;
    }
  }

  function send(form) {
    var text = buildMessage(form);

    // Вариант А (рекомендуемый): отправка на свой обработчик.
    // Токен бота лежит на стороне обработчика и в код сайта не попадает.
    if (CFG.formEndpoint) {
      var f = form.elements;
      return fetch(CFG.formEndpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: f.name.value.trim(),
          phone: f.phone.value.trim(),
          service: f.service ? f.service.value : '',
          comment: f.comment ? f.comment.value.trim() : '',
          page: window.location.href,
          text: text
        })
      }).then(function (r) {
        if (!r.ok) throw new Error('endpoint ' + r.status);
        return true;
      });
    }

    // Вариант Б: прямая отправка в Telegram Bot API.
    // Работает без сервера, но токен виден в config.js — см. README.
    if (CFG.telegram && CFG.telegram.botToken && CFG.telegram.chatId) {
      return fetch('https://api.telegram.org/bot' + CFG.telegram.botToken + '/sendMessage', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          chat_id: CFG.telegram.chatId,
          text: text,
          disable_web_page_preview: true
        })
      }).then(function (r) {
        if (!r.ok) throw new Error('telegram ' + r.status);
        return true;
      });
    }

    return Promise.reject(new Error('Не настроен приём заявок: скопируйте assets/config.example.js в assets/config.js'));
  }

  Array.prototype.forEach.call(forms, function (form) {
    form.addEventListener('submit', function (e) {
      e.preventDefault();

      // Ловушка для ботов: поле спрятано, человек его не заполнит.
      if (form.elements.company && form.elements.company.value) return;

      if (!validate(form)) return;

      var btn = form.querySelector('button[type="submit"]');
      var label = btn ? btn.textContent : '';
      if (btn) { btn.disabled = true; btn.textContent = 'Отправляем…'; }

      send(form)
        .then(function () {
          form.reset();
          showStatus(form, 'ok', form.getAttribute('data-success') || 'Заявка отправлена.');
        })
        .catch(function (err) {
          showStatus(form, 'err', form.getAttribute('data-error') || 'Не удалось отправить.');
          showRescue(form);   // заявку не теряем: даём готовые пути связи
          if (window.console) console.warn('[форма]', err.message);
        })
        .then(function () {
          if (btn) { btn.disabled = false; btn.textContent = label; }
        });
    });

    // Телефон: оставляем только осмысленные символы, не мешая вводу.
    var phone = form.elements.phone;
    if (phone) {
      phone.addEventListener('input', function () {
        phone.value = phone.value.replace(/[^\d+()\-\s]/g, '');
      });
    }
  });
})();
