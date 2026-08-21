/* =============================================================================
   ООО «МАСТЕР» - вся логика сайта.
   Библиотек нет, всё своё. Файл подключается с атрибутом defer.

   ВСЕ НАСТРОЙКИ - В БЛОКЕ CONFIG НИЖЕ. Больше в этом файле ничего менять не
   нужно. Что за что отвечает - подробно расписано в README.md.
   ========================================================================== */

var CONFIG = {

  /* Куда уходит заявка.
     'php'      - на send.php (рекомендуется; там же настраивается почта или
                  Telegram, и токен бота остаётся на сервере)
     'telegram' - напрямую в Telegram из браузера, без PHP.
                  Годится, если хостинг не умеет PHP.
                  ВНИМАНИЕ: при таком варианте токен бота видно всем, кто
                  откроет исходный код страницы. Подробности в README.md. */
  formMode: 'php',

  /* Адрес обработчика для formMode: 'php' */
  phpEndpoint: 'send.php',

  /* Заполняется только для formMode: 'telegram' */
  telegram: {
    token: '',
    chatId: ''
  },

  /* Номер счётчика Яндекс.Метрики. Пока стоит 00000000, счётчик не
     подключается и сайт вообще не обращается к Яндексу. */
  metrikaId: '00000000'
};

/* ========================================================================== */

(function () {
  'use strict';

  var root = document.documentElement;
  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function $(sel, ctx) { return (ctx || document).querySelector(sel); }
  function $$(sel, ctx) { return Array.prototype.slice.call((ctx || document).querySelectorAll(sel)); }

  /* ------------------------------------------------------------------------
     Яндекс.Метрика
     ---------------------------------------------------------------------- */

  var metrikaOn = CONFIG.metrikaId && !/^0+$/.test(String(CONFIG.metrikaId));

  function initMetrika() {
    if (!metrikaOn) return;
    (function (m, e, t, r, i, k, a) {
      m[i] = m[i] || function () { (m[i].a = m[i].a || []).push(arguments); };
      m[i].l = 1 * new Date();
      k = e.createElement(t); a = e.getElementsByTagName(t)[0];
      k.async = 1; k.src = r; a.parentNode.insertBefore(k, a);
    })(window, document, 'script', 'https://mc.yandex.ru/metrika/tag.js', 'ym');

    window.ym(CONFIG.metrikaId, 'init', {
      clickmap: true,
      trackLinks: true,
      accurateTrackBounce: true
    });
  }

  function goal(name) {
    if (metrikaOn && window.ym) window.ym(CONFIG.metrikaId, 'reachGoal', name);
  }

  /* Цель «клик по телефону» - на всех ссылках с data-goal="phone" */
  document.addEventListener('click', function (e) {
    var link = e.target.closest ? e.target.closest('[data-goal="phone"]') : null;
    if (link) goal('phone_click');
  });

  /* ------------------------------------------------------------------------
     Год в подвале
     ---------------------------------------------------------------------- */

  var yearEl = $('#year');
  if (yearEl) yearEl.textContent = String(new Date().getFullYear());

  /* ------------------------------------------------------------------------
     Бургер-меню
     ---------------------------------------------------------------------- */

  var burger = $('.burger');
  var mobileNav = $('#mobile-nav');

  function closeMenu() {
    if (!burger || !mobileNav) return;
    burger.setAttribute('aria-expanded', 'false');
    mobileNav.hidden = true;
  }

  if (burger && mobileNav) {
    burger.addEventListener('click', function () {
      var open = burger.getAttribute('aria-expanded') === 'true';
      burger.setAttribute('aria-expanded', String(!open));
      mobileNav.hidden = open;
    });

    $$('.mobile-nav__link, .mobile-nav__foot a', mobileNav).forEach(function (a) {
      a.addEventListener('click', closeMenu);
    });

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && burger.getAttribute('aria-expanded') === 'true') {
        closeMenu();
        burger.focus();
      }
    });

    window.addEventListener('resize', function () {
      if (window.innerWidth >= 1024) closeMenu();
    });
  }

  /* ------------------------------------------------------------------------
     Виды работ: на десктопе всё раскрыто, на мобильных - аккордеон
     ---------------------------------------------------------------------- */

  var accordion = $('[data-accordion]');

  if (accordion) {
    var heads = $$('.work__head', accordion);
    var narrow = window.matchMedia('(max-width: 1199px)');

    function setItem(head, open) {
      head.setAttribute('aria-expanded', String(open));
      var panel = document.getElementById(head.getAttribute('aria-controls'));
      if (panel) panel.hidden = !open;
    }

    function applyLayout() {
      heads.forEach(function (head, i) {
        setItem(head, narrow.matches ? i === 0 : true);
      });
    }

    heads.forEach(function (head) {
      head.addEventListener('click', function () {
        setItem(head, head.getAttribute('aria-expanded') !== 'true');
      });
    });

    applyLayout();
    if (narrow.addEventListener) narrow.addEventListener('change', applyLayout);
    else if (narrow.addListener) narrow.addListener(applyLayout);
  }

  /* ------------------------------------------------------------------------
     Появление блоков по скроллу
     ---------------------------------------------------------------------- */

  var reveals = $$('.reveal');

  if (reveals.length) {
    if (reduceMotion || !('IntersectionObserver' in window)) {
      reveals.forEach(function (el) { el.classList.add('is-in'); });
    } else {
      var revealObserver = new IntersectionObserver(function (entries, obs) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;
          var el = entry.target;
          el.classList.add('is-in');
          obs.unobserve(el);
          /* Блок появился - снимаем классы, чтобы браузер не держал под него
             отдельный слой композиции. Заодно исчезают артефакты отрисовки. */
          window.setTimeout(function () {
            el.classList.remove('reveal', 'is-in');
          }, 600);
        });
      }, { rootMargin: '0px 0px -12% 0px', threshold: 0.04 });

      reveals.forEach(function (el) { revealObserver.observe(el); });
    }
  }

  /* ------------------------------------------------------------------------
     Подсветка текущего раздела в меню
     ---------------------------------------------------------------------- */

  var navLinks = $$('.nav__link');

  if (navLinks.length && 'IntersectionObserver' in window) {
    var byId = {};
    navLinks.forEach(function (link) {
      byId[link.getAttribute('href').slice(1)] = link;
    });

    var sections = Object.keys(byId)
      .map(function (id) { return document.getElementById(id); })
      .filter(Boolean);

    var navObserver = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        var link = byId[entry.target.id];
        if (!link) return;
        if (entry.isIntersecting) {
          navLinks.forEach(function (l) { l.removeAttribute('aria-current'); });
          link.setAttribute('aria-current', 'true');
        }
      });
    }, { rootMargin: '-45% 0px -50% 0px' });

    sections.forEach(function (s) { navObserver.observe(s); });
  }

  /* ------------------------------------------------------------------------
     Лайтбокс галереи
     ---------------------------------------------------------------------- */

  var lb = $('#lightbox');

  if (lb) {
    var lbImg = $('#lb-img');
    var lbCap = $('#lb-cap');
    var lbCount = $('#lb-count');
    var lbPrev = $('#lb-prev');
    var lbNext = $('#lb-next');
    var lbClose = $('#lb-close');

    var items = [];
    var index = 0;
    var lastFocused = null;

    /* Поддерживает ли браузер webp. Если нет - показываем jpg. */
    var webpOk = (function () {
      var c = document.createElement('canvas');
      return !!(c.getContext && c.toDataURL('image/webp').indexOf('data:image/webp') === 0);
    })();

    function srcOf(tile) {
      return (webpOk ? tile.dataset.full : tile.dataset.fallback) || tile.dataset.fallback;
    }

    function show(i) {
      if (!items.length) return;
      index = (i + items.length) % items.length;
      var tile = items[index];
      var inner = tile.querySelector('img');
      lbImg.src = srcOf(tile);
      lbImg.alt = inner ? inner.alt : '';
      lbCap.textContent = tile.dataset.caption || (inner ? inner.alt : '');
      lbCount.textContent = (index + 1) + ' / ' + items.length;
      lbPrev.hidden = lbNext.hidden = items.length < 2;
    }

    function open(group, tile) {
      items = $$('.tile', group);
      lastFocused = tile;
      lb.hidden = false;
      document.body.style.overflow = 'hidden';
      show(items.indexOf(tile));
      lbClose.focus();
    }

    function close() {
      lb.hidden = true;
      /* Именно removeAttribute, а не src = '': пустой src браузер считает
         ссылкой на саму страницу и грузит её ещё раз. */
      lbImg.removeAttribute('src');
      lbImg.alt = '';
      document.body.style.overflow = '';
      if (lastFocused) lastFocused.focus();
    }

    $$('[data-lightbox-group]').forEach(function (group) {
      $$('.tile', group).forEach(function (tile) {
        tile.addEventListener('click', function () { open(group, tile); });
      });
    });

    lbClose.addEventListener('click', close);
    lbPrev.addEventListener('click', function () { show(index - 1); });
    lbNext.addEventListener('click', function () { show(index + 1); });

    lb.addEventListener('click', function (e) {
      if (e.target === lb || e.target.classList.contains('lightbox__stage')) close();
    });

    document.addEventListener('keydown', function (e) {
      if (lb.hidden) return;
      if (e.key === 'Escape') { close(); return; }
      if (e.key === 'ArrowLeft') { show(index - 1); return; }
      if (e.key === 'ArrowRight') { show(index + 1); return; }
      if (e.key !== 'Tab') return;

      /* Фокус не должен уходить из окна просмотра */
      var focusables = $$('button:not([hidden])', lb);
      if (!focusables.length) return;
      var first = focusables[0];
      var last = focusables[focusables.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault(); last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault(); first.focus();
      }
    });
  }

  /* ------------------------------------------------------------------------
     Яндекс.Карта - грузится только по нажатию
     ---------------------------------------------------------------------- */

  var mapBtn = $('#map-load');
  var mapBox = $('#map');

  if (mapBtn && mapBox) {
    mapBtn.addEventListener('click', function () {
      var frame = document.createElement('iframe');
      frame.src = mapBox.dataset.mapSrc;
      frame.title = 'Карта: Ростов-на-Дону, улица Петренко, 28';
      frame.loading = 'lazy';
      frame.setAttribute('allowfullscreen', '');
      frame.referrerPolicy = 'no-referrer-when-downgrade';
      mapBox.innerHTML = '';
      mapBox.appendChild(frame);
    });
  }

  /* ------------------------------------------------------------------------
     Форма заявки
     ---------------------------------------------------------------------- */

  var form = $('#lead-form');

  if (form) {
    var statusEl = $('#form-status');
    var doneEl = $('#form-done');
    var submitBtn = form.querySelector('button[type="submit"]');
    var tsField = $('#f-ts');

    if (tsField) tsField.value = String(Date.now());

    /* --- маска телефона --------------------------------------------------- */

    var phoneEl = $('#f-phone');

    function digitsOf(value) {
      return String(value).replace(/\D/g, '');
    }

    function formatPhone(value) {
      var d = digitsOf(value);
      if (!d) return '';
      if (d[0] === '8' || d[0] === '9') d = (d[0] === '8' ? '7' + d.slice(1) : '7' + d);
      if (d[0] !== '7') d = '7' + d;
      d = d.slice(0, 11);

      var out = '+7';
      if (d.length > 1) out += ' (' + d.slice(1, 4);
      if (d.length >= 5) out += ') ' + d.slice(4, 7);
      if (d.length >= 8) out += '-' + d.slice(7, 9);
      if (d.length >= 10) out += '-' + d.slice(9, 11);
      return out;
    }

    if (phoneEl) {
      phoneEl.addEventListener('input', function () {
        phoneEl.value = formatPhone(phoneEl.value);
      });
      phoneEl.addEventListener('blur', function () {
        if (digitsOf(phoneEl.value).length <= 1) phoneEl.value = '';
      });
    }

    /* --- проверка полей --------------------------------------------------- */

    /* Сообщение объясняет, что не так и что сделать. */
    var RULES = {
      name: function (v) {
        if (!v.trim()) return 'Напишите, как к вам обращаться';
        if (v.trim().length < 2) return 'Слишком коротко - нужно хотя бы две буквы';
        if (v.trim().length > 80) return 'Слишком длинно - не больше 80 символов';
        return '';
      },
      phone: function (v) {
        var d = digitsOf(v);
        if (!d || d.length <= 1) return 'Оставьте телефон, чтобы мы могли перезвонить';
        if (d.length !== 11) return 'Не хватает цифр. Нужно 11, например +7 (929) 555-50-00';
        return '';
      },
      email: function (v) {
        if (!v.trim()) return '';
        if (!/^[^\s@]+@[^\s@]+\.[a-zA-Zа-яА-Я]{2,}$/.test(v.trim())) {
          return 'Проверьте адрес: нужны знак @ и точка, например name@mail.ru';
        }
        return '';
      },
      message: function (v) {
        if (v.length > 2000) return 'Слишком длинный текст - не больше 2000 символов';
        return '';
      }
    };

    function setError(input, message) {
      var field = input.closest('.field');
      var errorEl = document.getElementById(input.getAttribute('aria-describedby'));
      if (errorEl) errorEl.textContent = message;
      if (field) field.classList.toggle('is-invalid', !!message);
      input.setAttribute('aria-invalid', message ? 'true' : 'false');
    }

    function validateField(input) {
      var rule = RULES[input.name];
      if (!rule) return true;
      var message = rule(input.value);
      setError(input, message);
      return !message;
    }

    $$('input[name], textarea[name]', form).forEach(function (input) {
      if (!RULES[input.name]) return;
      input.addEventListener('blur', function () { validateField(input); });
      input.addEventListener('input', function () {
        if (input.getAttribute('aria-invalid') === 'true') validateField(input);
      });
    });

    var consentEl = $('#f-consent');
    var consentWrap = $('#consent-wrap');
    var consentError = $('#e-consent');

    function validateConsent() {
      var ok = consentEl.checked;
      consentError.textContent = ok
        ? ''
        : 'Отметьте согласие на обработку данных - без него мы не вправе принять заявку';
      consentWrap.classList.toggle('is-invalid', !ok);
      consentEl.setAttribute('aria-invalid', ok ? 'false' : 'true');
      return ok;
    }

    consentEl.addEventListener('change', function () {
      if (consentEl.getAttribute('aria-invalid') === 'true') validateConsent();
    });

    function validateAll() {
      var firstBad = null;

      $$('input[name], textarea[name]', form).forEach(function (input) {
        if (!RULES[input.name]) return;
        if (!validateField(input) && !firstBad) firstBad = input;
      });

      if (!validateConsent() && !firstBad) firstBad = consentEl;
      return firstBad;
    }

    /* --- отправка --------------------------------------------------------- */

    function setStatus(text, state) {
      statusEl.textContent = text;
      if (state) statusEl.setAttribute('data-state', state);
      else statusEl.removeAttribute('data-state');
    }

    function showDone() {
      form.hidden = true;
      doneEl.hidden = false;
      doneEl.focus();
      goal('form_submit');
    }

    function sendToPhp(data) {
      data.append('ajax', '1');
      return fetch(CONFIG.phpEndpoint, {
        method: 'POST',
        body: data,
        headers: { 'Accept': 'application/json' }
      }).then(function (response) {
        return response.json().catch(function () {
          throw new Error('Сервер ответил неожиданным образом');
        }).then(function (json) {
          if (!response.ok || !json.ok) {
            var failure = new Error(json && json.error ? json.error : 'Не удалось отправить заявку');
            failure.fromServer = !!(json && json.error);
            throw failure;
          }
          return json;
        });
      });
    }

    function sendToTelegram(data) {
      var conf = CONFIG.telegram;
      if (!conf.token || !conf.chatId) {
        return Promise.reject(new Error('Отправка в Telegram не настроена'));
      }

      var lines = [
        'Заявка с сайта ООО «МАСТЕР»',
        '',
        'Имя: ' + data.get('name'),
        'Телефон: ' + data.get('phone')
      ];
      if (data.get('email')) lines.push('Почта: ' + data.get('email'));
      if (data.get('message')) lines.push('Комментарий: ' + data.get('message'));

      return fetch('https://api.telegram.org/bot' + conf.token + '/sendMessage', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          chat_id: conf.chatId,
          text: lines.join('\n'),
          disable_web_page_preview: true
        })
      }).then(function (response) {
        if (!response.ok) throw new Error('Telegram не принял сообщение');
        return response.json();
      });
    }

    form.addEventListener('submit', function (e) {
      e.preventDefault();

      var firstBad = validateAll();
      if (firstBad) {
        setStatus('Проверьте отмеченные поля', 'error');
        firstBad.focus();
        return;
      }

      var data = new FormData(form);

      /* Поле-ловушка заполнено - это робот. Делаем вид, что всё хорошо. */
      if (String(data.get('company') || '').trim()) {
        showDone();
        return;
      }

      submitBtn.disabled = true;
      setStatus('Отправляем...', null);

      var request = CONFIG.formMode === 'telegram' ? sendToTelegram(data) : sendToPhp(data);

      request.then(function () {
        setStatus('', null);
        showDone();
      }).catch(function (error) {
        submitBtn.disabled = false;
        var text = error && error.message ? error.message : 'Что-то пошло не так';
        if (!(error && error.fromServer)) {
          text += '. Проверьте связь или позвоните нам: +7 (929) 555-50-00';
        }
        setStatus(text, 'error');
      });
    });
  }

  /* ------------------------------------------------------------------------
     Запуск
     ---------------------------------------------------------------------- */

  initMetrika();
})();
