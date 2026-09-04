/* ==========================================================================
   Строй-Герой — вся интерактивность сайта.
   Чистый JavaScript без библиотек и внешних подключений.
   Каждый блок независим: если элемента нет на странице, блок просто молчит.
   ========================================================================== */

(function () {
  'use strict';

  var $ = function (sel, root) { return (root || document).querySelector(sel); };
  var $$ = function (sel, root) {
    return Array.prototype.slice.call((root || document).querySelectorAll(sel));
  };
  var store = {
    get: function (key, fallback) {
      try {
        var raw = localStorage.getItem('sg-' + key);
        return raw === null ? fallback : JSON.parse(raw);
      } catch (e) { return fallback; }
    },
    set: function (key, value) {
      try { localStorage.setItem('sg-' + key, JSON.stringify(value)); } catch (e) {}
    }
  };

  /* ======================================================================
     Короткое сообщение внизу экрана
     ====================================================================== */
  var toastTimer;
  function toast(text) {
    var note = $('[data-demo-note]');
    if (!note) return;
    note.textContent = text;
    note.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { note.hidden = true; }, 3200);
  }

  /* ======================================================================
     Тема: светлая / тёмная. Выбор запоминается на устройстве.
     Класс на <html> ставится ещё в <head>, чтобы не мигало при загрузке.
     ====================================================================== */
  function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    var meta = $('meta[name="theme-color"]');
    if (meta) meta.setAttribute('content', theme === 'dark' ? '#0e1117' : '#ffffff');
    $$('[data-theme-toggle]').forEach(function (btn) {
      btn.setAttribute('aria-label', theme === 'dark' ? 'Включить светлую тему' : 'Включить тёмную тему');
      btn.setAttribute('aria-pressed', theme === 'dark' ? 'true' : 'false');
    });
  }

  $$('[data-theme-toggle]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var next = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      store.set('theme', next);
      applyTheme(next);
    });
  });
  applyTheme(document.documentElement.getAttribute('data-theme') || 'light');
  document.documentElement.classList.add('theme-ready');

  /* ======================================================================
     Поиск: показываем, что запрос дошёл
     Настоящего поиска в макете нет — искать не по чему, прайса ещё нет.
     Но молча открывать каталог, будто ничего не вводили, тоже нельзя:
     человек решит, что кнопка сломана. Показываем сам запрос и честно
     пишем, откуда возьмутся результаты.
     ====================================================================== */
  (function () {
    var query = '';
    try {
      query = (new URLSearchParams(window.location.search).get('search') || '').trim();
    } catch (e) {
      query = '';
    }
    if (!query) return;

    var head = $('.page-head');
    if (!head) return;

    // Поле поиска в шапке заполняем тем же запросом — иначе непонятно,
    // что именно сейчас показано.
    var input = $('[data-search-input]');
    if (input) input.value = query;

    var box = document.createElement('div');
    box.className = 'search-result';
    box.setAttribute('role', 'status');

    var title = document.createElement('p');
    title.className = 'search-result__title';
    title.textContent = 'Поиск: «' + query + '»';

    var note = document.createElement('p');
    note.className = 'search-result__note';
    note.textContent =
      'Поиск заработает вместе с прайсом: сейчас искать не по чему. Ниже — раздел «' +
      (head.querySelector('h1') ? head.querySelector('h1').textContent : 'каталог') +
      '» целиком.';

    var reset = document.createElement('a');
    reset.className = 'search-result__reset';
    reset.href = 'catalog.html';
    reset.textContent = 'Сбросить поиск';

    box.appendChild(title);
    box.appendChild(note);
    box.appendChild(reset);
    head.parentNode.insertBefore(box, head.nextSibling);
  })();

  /* ======================================================================
     Подборки товаров каруселью: стрелки листают на видимую ширину,
     на краях гаснут. Работает и обычной прокруткой пальцем.
     ====================================================================== */
  $$('[data-slider]').forEach(function (box) {
    var line = $('[data-slider-line]', box);
    var prev = $('[data-slider-prev]', box);
    var next = $('[data-slider-next]', box);
    if (!line || !prev || !next) return;

    function refresh() {
      var max = line.scrollWidth - line.clientWidth;
      prev.disabled = line.scrollLeft <= 1;
      next.disabled = line.scrollLeft >= max - 1;
    }

    function step(dir) {
      var card = line.querySelector('.product-card');
      var by = card ? (card.offsetWidth + 16) * Math.max(1, Math.floor(line.clientWidth / (card.offsetWidth + 16))) : line.clientWidth;
      line.scrollBy({ left: dir * by, behavior: 'smooth' });
    }

    prev.addEventListener('click', function () { step(-1); });
    next.addEventListener('click', function () { step(1); });
    line.addEventListener('scroll', refresh, { passive: true });
    window.addEventListener('resize', refresh);
    refresh();
  });

  /* ======================================================================
     Липкая шапка: при прокрутке вниз ужимается
     ====================================================================== */
  var header = $('[data-header]');
  if (header) {
    var ticking = false;
    var onScroll = function () {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(function () {
        header.classList.toggle('is-compact', window.scrollY > 140);
        ticking = false;
      });
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  }

  /* ======================================================================
     Выпадающие списки, меню каталога, мобильное меню, подсказки поиска
     ====================================================================== */
  var dropdowns = $$('[data-dropdown]');

  function closeAllDropdowns(except) {
    dropdowns.forEach(function (dd) {
      if (dd === except) return;
      var toggle = $('[data-dropdown-toggle]', dd);
      var panel = $('[data-dropdown-panel]', dd);
      if (!toggle || !panel) return;
      toggle.setAttribute('aria-expanded', 'false');
      panel.hidden = true;
    });
  }

  dropdowns.forEach(function (dd) {
    var toggle = $('[data-dropdown-toggle]', dd);
    var panel = $('[data-dropdown-panel]', dd);
    if (!toggle || !panel) return;
    toggle.addEventListener('click', function (e) {
      e.stopPropagation();
      var open = toggle.getAttribute('aria-expanded') === 'true';
      closeAllDropdowns(dd);
      closeCatalog();
      closeSuggest();
      toggle.setAttribute('aria-expanded', open ? 'false' : 'true');
      panel.hidden = open;
    });
  });

  /* Меню каталога открывают две кнопки: «Каталог» и «Ещё разделы» */
  var catalogBtns = $$('[data-catalog-toggle]');
  var catalogMenu = $('[data-catalog-menu]');

  function setCatalog(open) {
    if (!catalogMenu) return;
    catalogBtns.forEach(function (b) {
      b.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
    catalogMenu.hidden = !open;
  }

  function closeCatalog() {
    setCatalog(false);
  }

  if (catalogBtns.length && catalogMenu) {
    catalogBtns.forEach(function (btn) {
      btn.addEventListener('click', function (e) {
        e.stopPropagation();
        var open = btn.getAttribute('aria-expanded') === 'true';
        closeAllDropdowns();
        closeSuggest();
        setCatalog(!open);
      });
    });
    catalogMenu.addEventListener('click', function (e) { e.stopPropagation(); });
  }

  var searchInput = $('[data-search-input]');
  var suggest = $('[data-search-suggest]');

  function closeSuggest() {
    if (suggest) suggest.hidden = true;
  }

  if (searchInput && suggest) {
    searchInput.addEventListener('focus', function () {
      closeAllDropdowns();
      closeCatalog();
      suggest.hidden = false;
    });
    searchInput.addEventListener('click', function (e) { e.stopPropagation(); });
    suggest.addEventListener('click', function (e) { e.stopPropagation(); });
  }

  var burger = $('[data-burger]');
  var mobileNav = $('[data-mobile-nav]');

  if (burger && mobileNav) {
    burger.addEventListener('click', function (e) {
      e.stopPropagation();
      var open = burger.getAttribute('aria-expanded') === 'true';
      burger.setAttribute('aria-expanded', open ? 'false' : 'true');
      mobileNav.hidden = open;
    });
  }

  document.addEventListener('click', function () {
    closeAllDropdowns();
    closeCatalog();
    closeSuggest();
  });

  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape') return;
    closeAllDropdowns();
    closeCatalog();
    closeSuggest();
    if (burger && mobileNav && !mobileNav.hidden) {
      burger.setAttribute('aria-expanded', 'false');
      mobileNav.hidden = true;
      burger.focus();
    }
  });

  /* ======================================================================
     Счётчики корзины, избранного и сравнения.
     Это макет: товары не настоящие, считаем только количество кликов,
     чтобы показать поведение интерфейса.
     ====================================================================== */
  var counters = {
    cart: store.get('cart', 0),
    fav: store.get('fav', 0),
    compare: store.get('compare', 0)
  };

  function renderCounters() {
    Object.keys(counters).forEach(function (key) {
      $$('[data-count="' + key + '"]').forEach(function (el) {
        el.textContent = counters[key];
        el.hidden = counters[key] === 0 && el.hasAttribute('data-hide-empty');
      });
    });
  }

  function bump(key, delta) {
    counters[key] = Math.max(0, counters[key] + delta);
    store.set(key, counters[key]);
    renderCounters();
    $$('[data-count="' + key + '"]').forEach(function (el) {
      el.classList.remove('is-pop');
      void el.offsetWidth; // перезапуск анимации
      el.classList.add('is-pop');
    });
  }

  renderCounters();

  document.addEventListener('click', function (e) {
    var btn = e.target.closest ? e.target.closest('[data-add]') : null;
    if (!btn) return;
    e.preventDefault();
    var kind = btn.getAttribute('data-add');
    if (kind === 'cart') {
      bump('cart', 1);
      toast('Товар добавлен в корзину. В макете корзина демонстрационная.');
    } else if (kind === 'fav') {
      var on = btn.classList.toggle('is-on');
      bump('fav', on ? 1 : -1);
      toast(on ? 'Добавлено в избранное' : 'Убрано из избранного');
    } else if (kind === 'compare') {
      var onC = btn.classList.toggle('is-on');
      bump('compare', onC ? 1 : -1);
      toast(onC ? 'Добавлено к сравнению' : 'Убрано из сравнения');
    }
  });

  /* ======================================================================
     Модальные окна на <dialog>: фокус и Esc обрабатывает сам браузер
     ====================================================================== */
  document.addEventListener('click', function (e) {
    var opener = e.target.closest ? e.target.closest('[data-modal-open]') : null;
    if (opener) {
      e.preventDefault();
      var dlg = document.getElementById(opener.getAttribute('data-modal-open'));
      if (dlg && typeof dlg.showModal === 'function') dlg.showModal();
      else if (dlg) dlg.setAttribute('open', '');
      return;
    }
    var closer = e.target.closest ? e.target.closest('[data-modal-close]') : null;
    if (closer) {
      var parent = closer.closest('dialog');
      if (parent) parent.close();
    }
  });

  // Клик по затемнению закрывает окно
  $$('dialog.modal').forEach(function (dlg) {
    dlg.addEventListener('click', function (e) {
      if (e.target === dlg) dlg.close();
    });
  });

  /* ======================================================================
     Вкладки на карточке товара
     ====================================================================== */
  var tabButtons = $$('[data-tab]');

  tabButtons.forEach(function (btn) {
    btn.addEventListener('click', function () {
      tabButtons.forEach(function (other) {
        var isCurrent = other === btn;
        other.setAttribute('aria-selected', isCurrent ? 'true' : 'false');
        var panel = document.getElementById(other.getAttribute('data-tab'));
        if (panel) panel.hidden = !isCurrent;
      });
    });
  });

  /* ======================================================================
     Счётчик количества
     ====================================================================== */
  $$('[data-qty]').forEach(function (box) {
    var input = $('input', box);
    if (!input) return;
    box.addEventListener('click', function (e) {
      var step = e.target.getAttribute && e.target.getAttribute('data-qty-step');
      if (!step) return;
      var value = parseInt(input.value, 10);
      if (isNaN(value)) value = 1;
      value += parseInt(step, 10);
      input.value = value < 1 ? 1 : value;
    });
  });

  /* ======================================================================
     Галерея: миниатюра становится активной
     ====================================================================== */
  var thumbs = $$('[data-thumb]');
  thumbs.forEach(function (t) {
    t.addEventListener('click', function () {
      thumbs.forEach(function (o) { o.setAttribute('aria-current', o === t ? 'true' : 'false'); });
    });
  });

  /* ======================================================================
     Каталог: фильтры, вид списком, чипы, ползунок цены
     ====================================================================== */
  var filtersToggle = $('[data-filters-toggle]');
  var filters = $('[data-filters]');

  if (filtersToggle && filters) {
    if (window.matchMedia('(max-width: 1023px)').matches) {
      filters.setAttribute('data-collapsed', 'true');
      filtersToggle.setAttribute('aria-expanded', 'false');
    }
    filtersToggle.addEventListener('click', function () {
      var collapsed = filters.getAttribute('data-collapsed') === 'true';
      filters.setAttribute('data-collapsed', collapsed ? 'false' : 'true');
      filtersToggle.setAttribute('aria-expanded', collapsed ? 'true' : 'false');
    });
  }

  var grid = $('[data-product-grid]');
  $$('[data-view]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var mode = btn.getAttribute('data-view');
      $$('[data-view]').forEach(function (b) {
        b.setAttribute('aria-pressed', b === btn ? 'true' : 'false');
      });
      if (grid) grid.classList.toggle('product-grid--list', mode === 'list');
      store.set('view', mode);
    });
  });

  if (grid && store.get('view', 'grid') === 'list') {
    grid.classList.add('product-grid--list');
    $$('[data-view]').forEach(function (b) {
      b.setAttribute('aria-pressed', b.getAttribute('data-view') === 'list' ? 'true' : 'false');
    });
  }

  document.addEventListener('click', function (e) {
    var chip = e.target.closest ? e.target.closest('[data-chip]') : null;
    if (!chip) return;
    chip.remove();
    toast('Фильтр снят. В макете список товаров не пересобирается.');
  });

  // Двойной ползунок цены
  var range = $('[data-range]');
  if (range) {
    var from = $('[data-range-from]', range);
    var to = $('[data-range-to]', range);
    var fill = $('.range__fill', range);
    var inFrom = $('[data-price-from]');
    var inTo = $('[data-price-to]');

    var paint = function () {
      var min = parseInt(from.min, 10);
      var max = parseInt(from.max, 10);
      var a = Math.min(parseInt(from.value, 10), parseInt(to.value, 10));
      var b = Math.max(parseInt(from.value, 10), parseInt(to.value, 10));
      fill.style.left = ((a - min) / (max - min)) * 100 + '%';
      fill.style.width = ((b - a) / (max - min)) * 100 + '%';
      if (inFrom) inFrom.value = a;
      if (inTo) inTo.value = b;
    };
    from.addEventListener('input', paint);
    to.addEventListener('input', paint);
    paint();
  }

  /* ======================================================================
     Кнопка «наверх»
     ====================================================================== */
  var toTop = $('[data-to-top]');
  if (toTop) {
    var toggleTop = function () {
      toTop.classList.toggle('is-visible', window.scrollY > 700);
    };
    window.addEventListener('scroll', toggleTop, { passive: true });
    toTop.addEventListener('click', function () {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
    toggleTop();
  }

  /* ======================================================================
     Появление блоков при прокрутке
     ====================================================================== */
  var revealables = $$('.reveal');
  if (revealables.length && 'IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        entry.target.classList.add('is-in');
        io.unobserve(entry.target);
      });
    }, { rootMargin: '0px 0px -60px 0px', threshold: 0.05 });
    revealables.forEach(function (el) { io.observe(el); });
  } else {
    revealables.forEach(function (el) { el.classList.add('is-in'); });
  }

  /* ======================================================================
     Плашка про cookie
     ====================================================================== */
  var cookie = $('[data-cookie]');
  if (cookie) {
    /* Пока плашка висит, странице добавляется отступ снизу ровно на её
       высоту. Иначе она закрывает то, что оказалось внизу экрана:
       на главной — заголовок и кнопки, в каталоге — первый ряд товаров.
       Отступ снимается вместе с плашкой, следов не остаётся. */
    var fitCookie = function () {
      document.body.style.setProperty('--cookie-h', cookie.offsetHeight + 'px');
    };
    if (!store.get('cookie-ok', false)) {
      cookie.hidden = false;
      document.body.classList.add('has-cookie');
      fitCookie();
      window.addEventListener('resize', fitCookie);
    }
    var okBtn = $('[data-cookie-ok]', cookie);
    if (okBtn) {
      okBtn.addEventListener('click', function () {
        store.set('cookie-ok', true);
        cookie.hidden = true;
        document.body.classList.remove('has-cookie');
        window.removeEventListener('resize', fitCookie);
      });
    }
  }

  /* ======================================================================
     Формы: маска телефона, проверка полей, сообщение об отправке
     ====================================================================== */
  $$('[data-phone-mask]').forEach(function (input) {
    input.addEventListener('input', function () {
      var digits = input.value.replace(/\D/g, '').replace(/^[78]/, '');
      var out = '+7';
      if (digits.length) out += ' (' + digits.substring(0, 3);
      if (digits.length >= 4) out += ') ' + digits.substring(3, 6);
      if (digits.length >= 7) out += '-' + digits.substring(6, 8);
      if (digits.length >= 9) out += '-' + digits.substring(8, 10);
      input.value = out;
    });
  });

  $$('[data-validate]').forEach(function (form) {
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var ok = true;

      $$('[required]', form).forEach(function (field) {
        var valid = field.type === 'checkbox' ? field.checked : field.value.trim().length > 1;
        field.setAttribute('aria-invalid', valid ? 'false' : 'true');
        var error = field.closest('.form__row, .consent');
        if (error) {
          var msg = $('.form__error', error);
          if (msg) msg.classList.toggle('is-shown', !valid);
        }
        if (!valid) ok = false;
      });

      if (!ok) {
        toast('Проверьте отмеченные поля');
        return;
      }

      var success = $('.form__success', form);
      if (success) success.classList.add('is-shown');
      form.reset();
      toast('В макете форма не отправляется — в рабочей версии письмо уйдёт на почту магазина.');
    });
  });

  /* ======================================================================
     Калькулятор материалов.
     Считает по обычным формулам и только по тем числам, которые ввёл
     пользователь. Никаких «средних расходов от производителя» не
     подставляем — расход и вес мешка человек берёт с упаковки.
     ====================================================================== */
  var calc = $('[data-calc]');
  if (calc) {
    var mode = 'gkl';

    /* По-русски дробная часть отделяется запятой, а тысячи — пробелом.
       Запятую на входе num() понимал и раньше, а на выходе везде печаталась
       точка: «20.0 м²», «3.00 м²». Для покупателя на Камчатке это выглядит
       как чужой формат, а в смете с такими числами легко ошибиться. */
    var ru = function (value, digits) {
      return Number(value).toLocaleString('ru-RU', {
        minimumFractionDigits: digits || 0,
        maximumFractionDigits: digits === undefined ? 2 : digits
      });
    };

    var num = function (sel) {
      var el = $(sel, calc);
      if (!el) return NaN;
      var v = parseFloat(String(el.value).replace(',', '.'));
      return isNaN(v) ? NaN : v;
    };

    var setMode = function (next) {
      mode = next;
      $$('[data-calc-mode]', calc).forEach(function (b) {
        b.setAttribute('aria-selected', b.getAttribute('data-calc-mode') === next ? 'true' : 'false');
      });
      $$('[data-calc-panel]', calc).forEach(function (p) {
        p.hidden = p.getAttribute('data-calc-panel') !== next;
      });
      recount();
    };

    var render = function (answer, unit, rows, hint) {
      var out = $('[data-calc-answer]', calc);
      var list = $('[data-calc-rows]', calc);
      var note = $('[data-calc-note]', calc);
      if (out) out.textContent = answer === null ? '—' : ru(answer) + ' ' + unit;
      if (list) {
        list.innerHTML = rows.map(function (r) {
          return '<li><span>' + r[0] + '</span><b>' + r[1] + '</b></li>';
        }).join('');
      }
      if (note) note.textContent = hint;
    };

    var recount = function () {
      var reserve = num('[data-calc-reserve]');
      if (isNaN(reserve)) reserve = 0;

      if (mode === 'gkl') {
        var area = num('[data-gkl-area]');
        var sheet = num('[data-gkl-sheet]');
        var layers = num('[data-gkl-layers]');
        if (isNaN(area) || area <= 0 || isNaN(sheet) || sheet <= 0) {
          render(null, '', [], 'Впишите площадь — и калькулятор посчитает листы.');
          return;
        }
        var need = area * (layers || 1) * (1 + reserve / 100);
        var sheets = Math.ceil(need / sheet);
        render(sheets, sheets === 1 ? 'лист' : (sheets < 5 ? 'листа' : 'листов'), [
          ['Площадь обшивки', ru(area * (layers || 1), 1) + ' м²'],
          ['Запас', ru(reserve) + ' %'],
          ['Площадь одного листа', ru(sheet, 2) + ' м²']
        ], 'Оценка по площади. Проёмы, подрезка и раскладка листов могут изменить число — уточните в магазине.');
        return;
      }

      // Смеси: шпатлёвка и штукатурка
      var sArea = num('[data-mix-area]');
      var thick = num('[data-mix-thick]');
      var usage = num('[data-mix-usage]');
      var bag = num('[data-mix-bag]');

      if (isNaN(sArea) || sArea <= 0 || isNaN(thick) || thick <= 0) {
        render(null, '', [], 'Впишите площадь и толщину слоя.');
        return;
      }
      if (isNaN(usage) || usage <= 0 || isNaN(bag) || bag <= 0) {
        render(null, '', [
          ['Площадь', ru(sArea) + ' м²'],
          ['Слой', ru(thick) + ' мм']
        ], 'Осталось вписать расход и вес мешка — оба числа указаны на упаковке смеси. Свои цифры мы не придумываем: у разных смесей расход отличается в разы.');
        return;
      }
      var kg = sArea * thick * usage * (1 + reserve / 100);
      var bags = Math.ceil(kg / bag);
      render(bags, bags === 1 ? 'мешок' : (bags < 5 ? 'мешка' : 'мешков'), [
        ['Нужно смеси', ru(Math.round(kg)) + ' кг'],
        ['Запас', ru(reserve) + ' %'],
        ['Вес мешка', ru(bag) + ' кг']
      ], 'Расход взят из вашей строки — сверьтесь с упаковкой конкретной смеси.');
    };

    $$('[data-calc-mode]', calc).forEach(function (btn) {
      btn.addEventListener('click', function () { setMode(btn.getAttribute('data-calc-mode')); });
    });
    calc.addEventListener('input', recount);
    calc.addEventListener('change', recount);
    setMode('gkl');
  }

  /* ======================================================================
     Заглушки нерабочих действий макета
     ====================================================================== */
  document.addEventListener('click', function (e) {
    var el = e.target.closest ? e.target.closest('[data-demo]') : null;
    if (!el) return;
    e.preventDefault();
    toast('Это демонстрационный макет: ' + (el.getAttribute('data-demo') || 'действие') + ' здесь пока не работает.');
  });
})();
