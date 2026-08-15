/* =========================================================================
   Скрипты сайта. Один файл на весь сайт, без библиотек.
   1. Мобильное меню
   2. Фоновое видео первого экрана (грузится только там, где нужно)
   3. Форма заявки -> Telegram
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

  /* Появления блоков при скролле здесь СОЗНАТЕЛЬНО НЕТ.
     Текст, спрятанный до попадания в кадр, пропадает при печати в PDF,
     при переходе по якорю и при любой ошибке в скриптах, а посетитель
     у нас торопится и читает по диагонали. Плавность сделана там, где
     она ничем не рискует: наведение, фокус, раскрытие вопросов, шапка. */

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
     Видео подключается ТОЛЬКО на широких экранах и только если пользователь
     не отключил анимации. На телефоне остаётся постер (картинка):
     не тратим трафик и батарею, не зависим от автозапуска в iOS.
     Источники подставляются скриптом, поэтому браузер не начинает качать
     видео до того, как мы разрешим.                                        */
  var video = document.querySelector('.hero__video');
  if (video) {
    var wide = window.matchMedia('(min-width: 981px)').matches;
    var calm = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var saveData = navigator.connection && navigator.connection.saveData;

    if (wide && !calm && !saveData) {
      var start = function () {
        var sources = (video.getAttribute('data-src') || '').split('|');
        sources.forEach(function (src) {
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
      // Ждём полной загрузки страницы: видео не задерживает первый экран.
      if (document.readyState === 'complete') start();
      else window.addEventListener('load', start);
    } else {
      video.remove();
    }
  }

  /* ---------- 3. Форма заявки -------------------------------------------- */
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
