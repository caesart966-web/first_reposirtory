/* Строй-Герой — минимальный ванильный JS.
   Только то, без чего интерфейс не работает: выпадающие списки,
   меню каталога, мобильное меню, вкладки на карточке товара,
   счётчик количества и сворачивание фильтров на телефоне.
   Никаких библиотек и внешних подключений. */

(function () {
  'use strict';

  /* ---------- Выпадающие списки (адреса, график работы) ---------- */
  var dropdowns = Array.prototype.slice.call(document.querySelectorAll('[data-dropdown]'));

  function closeAllDropdowns(except) {
    dropdowns.forEach(function (dd) {
      if (dd === except) return;
      var toggle = dd.querySelector('[data-dropdown-toggle]');
      var panel = dd.querySelector('[data-dropdown-panel]');
      if (!toggle || !panel) return;
      toggle.setAttribute('aria-expanded', 'false');
      panel.hidden = true;
    });
  }

  dropdowns.forEach(function (dd) {
    var toggle = dd.querySelector('[data-dropdown-toggle]');
    var panel = dd.querySelector('[data-dropdown-panel]');
    if (!toggle || !panel) return;

    toggle.addEventListener('click', function (e) {
      e.stopPropagation();
      var open = toggle.getAttribute('aria-expanded') === 'true';
      closeAllDropdowns(dd);
      closeCatalog();
      toggle.setAttribute('aria-expanded', open ? 'false' : 'true');
      panel.hidden = open;
    });
  });

  /* ---------- Меню каталога ---------- */
  var catalogBtn = document.querySelector('[data-catalog-toggle]');
  var catalogMenu = document.querySelector('[data-catalog-menu]');

  function closeCatalog() {
    if (!catalogBtn || !catalogMenu) return;
    catalogBtn.setAttribute('aria-expanded', 'false');
    catalogMenu.hidden = true;
  }

  if (catalogBtn && catalogMenu) {
    catalogBtn.addEventListener('click', function (e) {
      e.stopPropagation();
      var open = catalogBtn.getAttribute('aria-expanded') === 'true';
      closeAllDropdowns();
      catalogBtn.setAttribute('aria-expanded', open ? 'false' : 'true');
      catalogMenu.hidden = open;
    });
    catalogMenu.addEventListener('click', function (e) {
      e.stopPropagation();
    });
  }

  /* ---------- Мобильное меню ---------- */
  var burger = document.querySelector('[data-burger]');
  var mobileNav = document.querySelector('[data-mobile-nav]');

  if (burger && mobileNav) {
    burger.addEventListener('click', function (e) {
      e.stopPropagation();
      var open = burger.getAttribute('aria-expanded') === 'true';
      burger.setAttribute('aria-expanded', open ? 'false' : 'true');
      mobileNav.hidden = open;
    });
  }

  /* Клик мимо и Esc закрывают всё открытое */
  document.addEventListener('click', function () {
    closeAllDropdowns();
    closeCatalog();
  });

  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape') return;
    closeAllDropdowns();
    closeCatalog();
    if (burger && mobileNav && !mobileNav.hidden) {
      burger.setAttribute('aria-expanded', 'false');
      mobileNav.hidden = true;
      burger.focus();
    }
  });

  /* ---------- Вкладки на карточке товара ---------- */
  var tabButtons = Array.prototype.slice.call(document.querySelectorAll('[data-tab]'));

  tabButtons.forEach(function (btn) {
    btn.addEventListener('click', function () {
      var target = btn.getAttribute('data-tab');
      tabButtons.forEach(function (other) {
        var isCurrent = other === btn;
        other.setAttribute('aria-selected', isCurrent ? 'true' : 'false');
        var panel = document.getElementById(other.getAttribute('data-tab'));
        if (panel) panel.hidden = !isCurrent;
      });
      var panel = document.getElementById(target);
      if (panel) panel.hidden = false;
    });
  });

  /* ---------- Счётчик количества ---------- */
  var qtyBoxes = Array.prototype.slice.call(document.querySelectorAll('[data-qty]'));

  qtyBoxes.forEach(function (box) {
    var input = box.querySelector('input');
    if (!input) return;
    box.addEventListener('click', function (e) {
      var step = e.target.getAttribute && e.target.getAttribute('data-qty-step');
      if (!step) return;
      var value = parseInt(input.value, 10);
      if (isNaN(value)) value = 1;
      value += parseInt(step, 10);
      if (value < 1) value = 1;
      input.value = value;
    });
  });

  /* ---------- Фильтры: сворачиваются на узком экране ---------- */
  var filtersToggle = document.querySelector('[data-filters-toggle]');
  var filters = document.querySelector('[data-filters]');

  if (filtersToggle && filters) {
    // На телефоне фильтры по умолчанию свёрнуты, чтобы товары были сразу видны
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

  /* ---------- Заглушки нерабочих действий ----------
     Это концепт: корзина, избранное и оформление заказа не работают.
     Показываем короткое пояснение вместо молчаливого клика. */
  document.addEventListener('click', function (e) {
    var el = e.target.closest ? e.target.closest('[data-demo]') : null;
    if (!el) return;
    e.preventDefault();
    var note = document.querySelector('[data-demo-note]');
    if (!note) return;
    note.textContent = 'Это демонстрационный макет: ' + (el.getAttribute('data-demo') || 'действие') + ' здесь пока не работает.';
    note.hidden = false;
    clearTimeout(note._timer);
    note._timer = setTimeout(function () {
      note.hidden = true;
    }, 3000);
  });
})();
