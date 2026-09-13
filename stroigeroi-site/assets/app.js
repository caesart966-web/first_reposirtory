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
  /* Строка от человека уходит в innerHTML, поэтому экранируем. В макете
     подставить туда нечего, но привычка стоит дёшево, а в теме OpenCart
     этот же код будет получать настоящие поисковые запросы. */
  function escapeHtml(text) {
    return String(text).replace(/[&<>"']/g, function (ch) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch];
    });
  }

  /* Подсвечиваем в названии раздела ту часть, которую человек набрал.
     Ищем по нормализованной копии (нижний регистр, «ё» как «е»),
     а вырезаем из оригинала — иначе подсветка съела бы заглавные буквы. */
  function highlight(name, query) {
    var flat = name.toLowerCase().replace(/\u0451/g, '\u0435');
    var at = flat.indexOf(query);
    if (at < 0) return escapeHtml(name);
    return escapeHtml(name.slice(0, at)) +
      '<mark>' + escapeHtml(name.slice(at, at + query.length)) + '</mark>' +
      escapeHtml(name.slice(at + query.length));
  }

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

  /* Переключение темы. Плавным его делает не набор transition по
     свойствам — так плавнеют только заливки, а текст, рамки, значки
     и тени всё равно щёлкают, — а View Transition: браузер снимает
     кадр «до», меняет тему и переводит один кадр в другой целиком.
     Где этого API нет, тема просто меняется сразу, как раньше. */
  var themeRun = 0;

  function switchTheme(next) {
    store.set('theme', next);
    var smooth = typeof document.startViewTransition === 'function' &&
      !window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (!smooth) {
      applyTheme(next);
      return;
    }
    var root = document.documentElement;
    /* На время перехода снимаем собственные transition заливок:
       иначе поверх кросс-фейда идёт вторая, своя анимация. */
    root.classList.add('is-theme-vt');
    /* Номер нужен на частые нажатия: новый переход отменяет прежний,
       у отменённого срабатывает finished — и без этой сверки он снял бы
       класс из-под уже идущего перехода. */
    var mine = ++themeRun;
    var done = function () { if (mine === themeRun) root.classList.remove('is-theme-vt'); };
    try {
      document.startViewTransition(function () { applyTheme(next); })
        .finished.then(done, done);
    } catch (e) {
      applyTheme(next);
      done();
    }
  }

  $$('[data-theme-toggle]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      switchTheme(document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark');
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
      'По разделам каталога поиск уже работает — подсказки появляются прямо в строке. ' +
      'По товарам он заработает вместе с прайсом: сейчас искать не по чему. Ниже — раздел «' +
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

    /* Настоящая высота шапки — в переменную, из которой стили берут
       отступ для якорей и верх липких панелей. Раньше эти числа стояли
       в CSS вручную (96 px для якорей, 16 для фильтров) и подходили
       только под широкий экран: на телефоне шапка держится 130 px,
       на планшете 142, и всё, к чему переходили по ссылке, оказывалось
       под ней. Шапка ещё и ужимается при прокрутке, поэтому высота
       меряется наблюдателем, а не один раз при загрузке. */
    var publishHeight = function () {
      document.documentElement.style.setProperty(
        '--header-now', Math.round(header.getBoundingClientRect().height) + 'px');
    };
    if ('ResizeObserver' in window) {
      new ResizeObserver(publishHeight).observe(header);
    } else {
      window.addEventListener('resize', publishHeight);
      window.addEventListener('scroll', publishHeight, { passive: true });
    }
    publishHeight();
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
    var suggestTitle = $('.search-suggest__title', suggest);
    var suggestList = $('.search-suggest__list', suggest);
    /* Разделы берём из меню каталога, а не переписываем сюда списком:
       иначе он однажды разойдётся с настоящим меню, и поиск начнёт
       предлагать разделы, которых на сайте уже нет. */
    var sections = $$('.catalog-menu__link').map(function (link) {
      return {
        name: link.textContent.trim(),
        href: link.getAttribute('href'),
        path: link.getAttribute('data-oc-path') || '',
        route: link.getAttribute('data-oc-route') || ''
      };
    });
    /* Список, который виден до ввода запроса. В макете он свёрстан
       в разметке; в теме OpenCart разделы в шапку не приходят, и там
       он пуст — тогда собираем его из тех же sections. Разметку берём
       ту же, что у найденных разделов, иначе до и после ввода запроса
       подсказки выглядели бы по-разному. */
    var defaultList = suggestList ? suggestList.innerHTML.trim() : '';
    if (suggestList && !defaultList && sections.length) {
      defaultList = sections.slice(0, 8).map(function (s) {
        return '<a class="search-suggest__item" href="' + s.href + '">' +
          escapeHtml(s.name) + '</a>';
      }).join('');
      suggestList.innerHTML = defaultList;
    }
    var defaultTitle = suggestTitle ? suggestTitle.textContent : '';

    /* Ищем по началу слова, а не по любому месту строки: «сад» должно
       находить «Всё для сада», но не «Расходка». Регистр и «ё» не важны. */
    var norm = function (s) { return s.toLowerCase().replace(/ё/g, 'е'); };
    var matches = function (name, query) {
      var words = norm(name).split(/[^a-zа-я0-9]+/);
      return words.some(function (w) { return w.indexOf(query) === 0; });
    };

    var renderSuggest = function () {
      if (!suggestList) return;
      var query = norm(searchInput.value.trim());
      if (!query) {
        suggestList.innerHTML = defaultList;
        if (suggestTitle) suggestTitle.textContent = defaultTitle;
        return;
      }
      var found = sections.filter(function (s) { return matches(s.name, query); });
      if (!found.length) {
        if (suggestTitle) suggestTitle.textContent = 'Ничего не нашлось';
        suggestList.innerHTML =
          '<p class="search-suggest__empty">По запросу «' + escapeHtml(searchInput.value.trim()) +
          '» раздела нет. Товары в макет ещё не загружены — позвоните ' +
          '<a class="tel-inline" href="tel:+79638300999">8-963-830-09-99</a>, подскажем, есть ли в магазине.</p>';
        return;
      }
      if (suggestTitle) {
        suggestTitle.textContent = found.length === 1 ? 'Нашёлся раздел' : 'Разделы: ' + found.length;
      }
      suggestList.innerHTML = found.map(function (s) {
        /* У адресов движка уже есть «?» (index.php?route=...), и второй
           вопросительный знак сделал бы ссылку битой. В макете адреса
           простые, и знак остаётся прежним. */
        var join = s.href.indexOf('?') >= 0 ? '&' : '?';
        return '<a class="search-suggest__item" href="' + s.href + join + 'search=' +
          encodeURIComponent(searchInput.value.trim()) + '"' +
          (s.path ? ' data-oc-path="' + s.path + '"' : '') +
          (s.route ? ' data-oc-route="' + s.route + '"' : '') +
          '>' + highlight(s.name, query) + '</a>';
      }).join('');
    };

    searchInput.addEventListener('focus', function () {
      closeAllDropdowns();
      closeCatalog();
      renderSuggest();
      suggest.hidden = false;
    });
    searchInput.addEventListener('input', function () {
      renderSuggest();
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
  /* В теме OpenCart счётчик корзины приходит с сервера: движок знает
     её настоящее содержимое ещё до отрисовки страницы, и число не прыгает
     при загрузке. Такой счётчик помечен data-count-server. В макете
     пометки нет, и значение берётся из памяти браузера, как и раньше. */
  function startCount(key, fallback) {
    var el = $('[data-count="' + key + '"][data-count-server]');
    if (!el) return fallback;
    var n = parseInt(el.textContent, 10);
    return isNaN(n) ? fallback : n;
  }

  var counters = {
    cart: startCount('cart', store.get('cart', 0)),
    fav: startCount('fav', store.get('fav', 0)),
    compare: startCount('compare', store.get('compare', 0))
  };

  function renderCounters() {
    Object.keys(counters).forEach(function (key) {
      $$('[data-count="' + key + '"]').forEach(function (el) {
        el.textContent = counters[key];
        el.hidden = counters[key] === 0 && el.hasAttribute('data-hide-empty');
      });
    });
  }

  /* Адреса движка для кнопок карточки. Разложены таблицей, а не
     условиями по месту: добавится четвёртая кнопка — добавится строка. */
  var SHOP_ROUTES = {
    cart:    { url: 'index.php?route=checkout/cart/add',    body: function (id) { return 'product_id=' + id + '&quantity=1'; } },
    fav:     { url: 'index.php?route=account/wishlist/add', body: function (id) { return 'product_id=' + id; } },
    compare: { url: 'index.php?route=product/compare/add',  body: function (id) { return 'product_id=' + id; } }
  };

  /* Движок отвечает готовой разметкой со ссылками («Товар добавлен,
     перейдите в корзину»). В строку внизу экрана она не годится —
     оставляем только текст. */
  function plainText(html) {
    var box = document.createElement('div');
    box.innerHTML = html;
    return box.textContent.replace(/\s+/g, ' ').trim();
  }

  function refreshCartCount() {
    fetch('index.php?route=common/cart/info', {
      headers: { 'X-Requested-With': 'XMLHttpRequest' }
    }).then(function (response) {
      return response.text();
    }).then(function (html) {
      var box = document.createElement('div');
      box.innerHTML = html;
      var fresh = box.querySelector('[data-count="cart"]');
      if (!fresh) return;
      var value = parseInt(fresh.textContent, 10);
      if (isNaN(value)) return;
      counters.cart = value;
      store.set('cart', value);
      renderCounters();
    }).catch(function () {});
  }

  function shopAdd(kind, id, btn) {
    var route = SHOP_ROUTES[kind];
    if (!route) return;
    btn.disabled = true;
    fetch(route.url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'X-Requested-With': 'XMLHttpRequest'
      },
      body: route.body(id)
    }).then(function (response) {
      return response.json();
    }).then(function (result) {
      /* Избранное требует входа в кабинет: движок отвечает адресом,
         куда отправить человека. Молча ничего не делать нельзя —
         он решит, что кнопка сломана. */
      if (result && result.redirect) {
        location.href = result.redirect;
        return;
      }
      if (result && result.success) {
        toast(plainText(result.success));
        if (kind === 'cart') {
          refreshCartCount();
        } else {
          btn.classList.add('is-on');
        }
        return;
      }
      var said = result && result.error;
      toast(typeof said === 'string' && said ? plainText(said) : 'Не получилось добавить товар');
    }).catch(function () {
      toast('Не получилось добавить товар. Попробуйте ещё раз.');
    }).then(function () {
      btn.disabled = false;
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

    /* В теме у кнопки есть номер товара — значит, работаем с настоящей
       корзиной движка, а не с памятью браузера. В макете номеров нет
       (товары безымянные, прайса ещё нет), и кнопка ведёт себя по-старому. */
    var productId = btn.getAttribute('data-product-id');
    if (productId) {
      shopAdd(kind, productId, btn);
      return;
    }

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
     Избранное и сравнение: показываем то, что человек отложил

     Товары в макете безымянные — прайса нет, все карточки одинаковые.
     Поэтому запоминается не «какой именно товар», а сколько их отложено,
     и страница разворачивает столько же карточек из шаблона. Для показа
     сценария этого достаточно: человек нажал три раза — видит три
     карточки и может убрать любую. С настоящим прайсом сюда встанут
     номера товаров, а разметка и поведение останутся теми же.
     ====================================================================== */
  var COMPARE_MAX = 4;

  function renderFavourites() {
    var list = $('[data-fav-list]');
    if (!list) return;
    var empty = $('[data-fav-empty]');
    var summary = $('[data-fav-summary]');
    var clear = $('[data-clear="fav"]');
    var tpl = $('[data-card-template]');
    var count = Math.max(0, counters.fav);

    list.innerHTML = '';
    for (var i = 0; i < count; i++) {
      list.appendChild(tpl.content.cloneNode(true));
    }
    list.hidden = count === 0;
    if (empty) empty.hidden = count > 0;
    if (clear) clear.hidden = count === 0;
    if (summary) {
      summary.textContent = count
        ? 'Отложено: ' + count + ' ' + plural(count, 'товар', 'товара', 'товаров')
        : '';
    }
  }

  function renderCompare() {
    var head = $('[data-compare-head]');
    if (!head) return;
    var box = $('[data-compare-box]');
    var empty = $('[data-compare-empty]');
    var summary = $('[data-compare-summary]');
    var clear = $('[data-clear="compare"]');
    var more = $('[data-compare-more]');
    var count = Math.min(COMPARE_MAX, Math.max(0, counters.compare));

    /* Убираем прежние столбцы, оставляя первый — с названиями строк */
    while (head.children.length > 1) head.removeChild(head.lastChild);
    $$('[data-compare-body] tr').forEach(function (row) {
      while (row.children.length > 1) row.removeChild(row.lastChild);
    });

    for (var i = 1; i <= count; i++) {
      var th = document.createElement('th');
      th.setAttribute('scope', 'col');
      th.innerHTML = '<span class="ph ph--inline">товар ' + i + '</span>';
      head.appendChild(th);

      $$('[data-compare-body] tr').forEach(function (row) {
        var td = document.createElement('td');
        var label = row.getAttribute('data-row') === 'Остаток' ? 'из учётной системы'
          : row.getAttribute('data-row') === 'Цена' ? 'цена, ₽' : 'из прайса';
        td.innerHTML = '<span class="ph ph--inline">' + label + '</span>';
        row.appendChild(td);
      });
    }

    if (box) box.hidden = count === 0;
    if (empty) empty.hidden = count > 0;
    if (clear) clear.hidden = count === 0;
    if (more) more.hidden = count === 0;
    if (summary) {
      summary.textContent = count
        ? 'В сравнении: ' + count + ' из ' + COMPARE_MAX
        : '';
    }
  }

  function plural(n, one, few, many) {
    var mod10 = n % 10, mod100 = n % 100;
    if (mod10 === 1 && mod100 !== 11) return one;
    if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return few;
    return many;
  }

  renderFavourites();
  renderCompare();

  /* Убрать одну карточку и очистить список целиком */
  document.addEventListener('click', function (e) {
    var remove = e.target.closest ? e.target.closest('[data-remove]') : null;
    if (remove) {
      bump(remove.getAttribute('data-remove'), -1);
      renderFavourites();
      toast('Убрано из избранного');
      return;
    }
    var clear = e.target.closest ? e.target.closest('[data-clear]') : null;
    if (clear) {
      var what = clear.getAttribute('data-clear');
      /* Через bump, а не записью в хранилище напрямую: счётчик живёт
         ещё и в памяти страницы, и прямая запись их рассинхронизирует. */
      bump(what, -counters[what]);
      renderFavourites();
      renderCompare();
      toast(what === 'fav' ? 'Избранное очищено' : 'Сравнение очищено');
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
      cartEdit(input);
    });
    input.addEventListener('change', function () { cartEdit(input); });
  });

  /* Изменение количества в корзине. В теме у поля есть номер строки
     корзины, и новое количество надо отправить движку — иначе человек
     поменяет цифру, увидит старую сумму и решит, что корзина врёт.
     Страница после ответа перезагружается: пересчитать надо не только
     строку, но и скидки, доставку и итог, а их считает сервер.
     В макете номеров строк нет, и функция ничего не делает. */
  var cartTimer;
  function cartEdit(input) {
    var key = input.getAttribute('data-cart-key');
    if (!key) return;
    var value = parseInt(input.value, 10);
    if (isNaN(value) || value < 1) return;
    clearTimeout(cartTimer);
    cartTimer = setTimeout(function () {
      fetch('index.php?route=checkout/cart/edit', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
          'X-Requested-With': 'XMLHttpRequest'
        },
        body: 'key=' + encodeURIComponent(key) + '&quantity=' + value
      }).then(function () { location.reload(); })
        .catch(function () { toast('Не получилось изменить количество'); });
    }, 500);
  }

  document.addEventListener('click', function (e) {
    var remove = e.target.closest ? e.target.closest('[data-cart-remove]') : null;
    if (!remove) return;
    e.preventDefault();
    remove.disabled = true;
    fetch('index.php?route=checkout/cart/remove', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'X-Requested-With': 'XMLHttpRequest'
      },
      body: 'key=' + encodeURIComponent(remove.getAttribute('data-cart-remove'))
    }).then(function () { location.reload(); })
      .catch(function () {
        remove.disabled = false;
        toast('Не получилось удалить товар');
      });
  });

  /* ======================================================================
     Галерея: миниатюра становится активной
     ====================================================================== */
  var thumbs = $$('[data-thumb]');
  var mainPhoto = $('#product-photo');
  thumbs.forEach(function (t) {
    t.addEventListener('click', function () {
      thumbs.forEach(function (o) { o.setAttribute('aria-current', o === t ? 'true' : 'false'); });
      /* В теме у миниатюры есть адрес крупного снимка, и главная
         фотография меняется. В макете снимков нет — миниатюры только
         подсвечиваются, как и раньше. */
      var full = t.getAttribute('data-full');
      if (full && mainPhoto) mainPhoto.src = full;
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
  /* Если браузер умеет scroll-driven анимации, появление уже посчитано
     в CSS — наблюдатель тут только мешал бы. Остальным собираем его
     по-старому. */
  var cssReveal = window.CSS && CSS.supports && CSS.supports('animation-timeline', 'view()');
  var revealables = cssReveal ? [] : $$('.reveal');
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
     «Сейчас открыто» у карточек магазинов
     ======================================================================

     Считаем по времени Камчатки, а не по часам устройства: магазины
     на Камчатке, и гость из Москвы иначе увидел бы «открыто» в час ночи
     по местному. Часовой пояс берём у самого браузера через Intl —
     сдвиг +12 руками не пишем, чтобы не разойтись с действительностью,
     если его когда-нибудь поменяют.

     Часы лежат в самой разметке (data-hours-*), там же они написаны
     словами: без JS человек видит расписание, просто без отметки.
     У Чубарова выходные начинаются позже, поэтому у каждой карточки
     свои значения, а не одно общее на три. */
  var KAMCHATKA = 'Asia/Kamchatka';

  function kamchatkaNow(when) {
    var f = new Intl.DateTimeFormat('en-GB', {
      timeZone: KAMCHATKA, weekday: 'short', hour: '2-digit', minute: '2-digit', hour12: false
    });
    var got = {};
    f.formatToParts(when || new Date()).forEach(function (p) { got[p.type] = p.value; });
    var days = { Mon: 1, Tue: 2, Wed: 3, Thu: 4, Fri: 5, Sat: 6, Sun: 0 };
    return { day: days[got.weekday], minutes: (+got.hour) * 60 + (+got.minute) };
  }

  function toMinutes(hhmm) {
    var p = String(hhmm).split(':');
    return (+p[0]) * 60 + (+p[1]);
  }

  function trimHour(hhmm) {
    return String(hhmm).replace(/^0/, '');
  }

  /* Возвращает готовую подпись для карточки. Вынесено отдельно, чтобы
     проверка могла прогнать её на заданном времени, а не ждать субботы. */
  function shopState(weekday, weekend, now) {
    var isWeekend = function (d) { return d === 0 || d === 6; };
    var todays = (isWeekend(now.day) ? weekend : weekday).split('-');
    var opens = toMinutes(todays[0]);
    var closes = toMinutes(todays[1]);

    if (now.minutes >= opens && now.minutes < closes) {
      return { open: true, text: 'Сейчас открыто, до ' + trimHour(todays[1]) };
    }
    if (now.minutes < opens) {
      return { open: false, text: 'Сейчас закрыто, откроется в ' + trimHour(todays[0]) };
    }
    var tomorrow = (now.day + 1) % 7;
    var next = (isWeekend(tomorrow) ? weekend : weekday).split('-');
    return { open: false, text: 'Сейчас закрыто, завтра с ' + trimHour(next[0]) };
  }

  $$('[data-hours-weekday]').forEach(function (row) {
    var mark = row.querySelector('[data-hours-now]');
    if (!mark || !window.Intl) return;
    var show = function () {
      var state = shopState(row.getAttribute('data-hours-weekday'),
                            row.getAttribute('data-hours-weekend'), kamchatkaNow());
      mark.textContent = state.text;
      mark.className = 'shop-card__now shop-card__now--' + (state.open ? 'open' : 'closed');
      mark.hidden = false;
    };
    show();
    /* Страницу держат открытой подолгу; раз в минуту отметка обновляется,
       иначе в 19:00 она так и будет уверять, что магазин работает. */
    setInterval(show, 60000);
  });

  /* Наружу — для проверок */
  window.sgShopState = shopState;

  /* ======================================================================
     Карты магазинов: если виджет не загрузился — показать адрес
     ======================================================================

     Когда запрос к Яндексу не проходит (нет сети, блокировщик, закрытый
     доступ), браузер рисует в кадре свой серый «битый документ» поверх
     запасной надписи — выходит хуже, чем пустое место было раньше.

     Отличить это изнутри страницы нельзя, я пробовал: событие load
     приходит и для страницы ошибки (за 216 мс), а contentDocument в обоих
     случаях null — свою страницу ошибки браузер тоже отдаёт как чужой
     источник. Поэтому доступность Яндекса проверяется отдельным запросом:
     при mode: 'no-cors' он отклоняется, только если запрос не прошёл.

     Запрос уходит один на все три карты и только когда до карты долистали:
     карты ленивые, до этого момента они и сами ничего не запрашивают. */
  var mapBoxes = $$('.shop-card__map');
  if (mapBoxes.length && window.fetch) {
    var probe = null;
    var checkMaps = function () {
      if (probe) return;
      probe = fetch('https://yandex.ru/favicon.ico', { mode: 'no-cors', cache: 'no-store' })
        .catch(function () {
          mapBoxes.forEach(function (box) { box.classList.add('is-mapfail'); });
        });
    };
    if ('IntersectionObserver' in window) {
      var mapIo = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;
          mapIo.unobserve(entry.target);
          checkMaps();
        });
      }, { rootMargin: '200px' });
      mapBoxes.forEach(function (box) { mapIo.observe(box); });
    } else {
      checkMaps();
    }
  }

  /* ======================================================================
     Печать списка покупок
     Ходовой сценарий для стройматериалов: собрал корзину, распечатал,
     поехал в магазин. Печатает браузер, ничего никуда не отправляется.
     ====================================================================== */
  $$('[data-print-cart]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      /* Дату ставим в момент печати, а не в разметку: лист без даты
         через неделю невозможно отличить от вчерашнего. */
      var stamp = $('[data-print-date]');
      if (stamp) {
        stamp.textContent = new Date().toLocaleDateString('ru-RU', {
          day: 'numeric', month: 'long', year: 'numeric'
        });
      }
      window.print();
    });
  });

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

      /* В теме OpenCart у формы есть адрес обработчика, и отправлять её
         надо по-настоящему. В макете action нет ни у одной из форм,
         поэтому сюда управление не заходит и поведение не меняется. */
      var action = form.getAttribute('action');
      if (action) {
        var button = $('button[type="submit"]', form);
        if (button) button.disabled = true;
        fetch(action, {
          method: 'POST',
          body: new FormData(form),
          headers: { 'X-Requested-With': 'XMLHttpRequest' }
        }).then(function (response) {
          return response.json();
        }).then(function (result) {
          if (result && result.redirect) {
            location.href = result.redirect;
            return;
          }
          if (result && result.success) {
            /* Добавление в корзину - не «заявка принята»: показываем ответ
               движка и обновляем счётчик, иначе цифра в шапке отстанет
               от настоящего содержимого корзины. */
            if (form.hasAttribute('data-product-form')) {
              toast(plainText(result.success));
              refreshCartCount();
              return;
            }
            var done = $('.form__success', form);
            if (done) done.classList.add('is-shown');
            form.reset();
            return;
          }
          /* Ответ обработчика показываем как есть: он объясняет, что
             именно не так, а общее «ошибка» человеку ничего не даёт.
             Движок на незаполненный обязательный параметр товара
             отвечает не строкой, а набором сообщений по полям. */
          var said = result && (result.error || result.error_name ||
            result.error_phone || result.error_consent);
          if (said && typeof said === 'object') {
            said = Object.keys(said).map(function (key) { return said[key]; }).join(' ');
          }
          toast(said ? plainText(String(said)) : 'Не получилось отправить. Позвоните нам: 8-963-830-09-99.');
        }).catch(function () {
          toast('Не получилось отправить. Позвоните нам: 8-963-830-09-99.');
        }).then(function () {
          if (button) button.disabled = false;
        });
        return;
      }

      /* Форма оформления ведёт на следующий шаг сценария. Без этого
         страница «Заказ принят» существовала, но кликом до неё было
         не дойти: форма молча сбрасывалась и показывала уведомление —
         тупик ровно там, где заказчик смотрит путь до конца. */
      var next = form.getAttribute('data-success-url');
      if (next) {
        window.location.href = next;
        return;
      }

      var success = $('.form__success', form);
      if (success) success.classList.add('is-shown');
      form.reset();
      toast('В макете форма не отправляется — в рабочей версии письмо уйдёт на почту магазина.');
    });
  });

  /* ======================================================================
     Две вещи, нужные только в теме OpenCart. В макете обе ничего не делают:
     первая ищет тег <base>, второй в макете нет; вторая заполняет списки,
     которые в макете уже заполнены.
     ====================================================================== */

  /* В теме в <head> стоит <base href>. При нём ссылка «#main» указывает
     не на текущую страницу, а на главную с этим якорем: человек жмёт
     «Перейти к содержимому» и уезжает с раздела на главную. Переписываем
     такие ссылки на полный адрес текущей страницы. */
  if (document.querySelector('base')) {
    var here = location.pathname + location.search;
    $$('a[href^="#"]').forEach(function (link) {
      var target = link.getAttribute('href');
      if (target.length > 1) link.setAttribute('href', here + target);
    });
  }

  /* Выпадающий список, который сам переводит на выбранный адрес.
     В теме так работает сортировка каталога: движок отдаёт готовые адреса,
     у каждого свой порядок. Встроенных onchange в разметке этого сайта нет
     нигде, поэтому переход делается здесь, по пометке. В макете таких
     списков нет, и код не делает ничего. */
  $$('[data-go-on-change]').forEach(function (select) {
    select.addEventListener('change', function () {
      if (select.value) location.href = select.value;
    });
  });

  /* Колонку «Каталог» в подвале заполняем из меню каталога — из разметки,
     которая на странице уже есть. Второй список тех же разделов рано или
     поздно разошёлся бы с первым. Подсказки под строкой поиска берут
     разделы оттуда же, но это делает сам модуль поиска выше. */
  var catalogLinks = $$('.catalog-menu__link').filter(function (link) {
    return !link.classList.contains('catalog-menu__link--special');
  });

  if (catalogLinks.length) {
    /* Сетка разделов на главной. Настоящие разделы приходят из меню
       каталога; карточка «Все разделы», свёрстанная в шаблоне, остаётся
       последней — без javascript она единственная, и сетка не пустует. */
    $$('[data-fill-cards]').forEach(function (grid) {
      var last = grid.lastElementChild;
      catalogLinks.forEach(function (source) {
        var card = document.createElement('a');
        card.className = 'category-card reveal';
        card.href = source.getAttribute('href');
        var icon = $('svg', source);
        if (icon) {
          var box = document.createElement('span');
          box.className = 'category-card__icon';
          box.appendChild(icon.cloneNode(true));
          card.appendChild(box);
        }
        var title = document.createElement('span');
        title.className = 'category-card__title';
        title.textContent = source.textContent.trim();
        card.appendChild(title);
        grid.insertBefore(card, last);
      });
    });

    $$('[data-fill-categories]').forEach(function (list) {
      var howMany = parseInt(list.getAttribute('data-fill-categories'), 10) || 4;
      var before = list.firstElementChild;
      catalogLinks.slice(0, howMany).forEach(function (source) {
        var row = document.createElement('li');
        var link = document.createElement('a');
        link.href = source.getAttribute('href');
        link.textContent = source.textContent.trim();
        row.appendChild(link);
        list.insertBefore(row, before);
      });
    });
  }

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
