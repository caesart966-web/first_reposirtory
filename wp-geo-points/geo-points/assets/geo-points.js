/**
 * Карта по клику. Фасад — настоящая кнопка, поэтому работает и с клавиатуры,
 * и со скринридера; после вставки фокус уходит на саму карту, иначе
 * нажавший клавишей остаётся стоять на исчезнувшей кнопке.
 */
(function () {
	'use strict';

	function load(box) {
		var src = box.getAttribute('data-src');
		if (!src || box.querySelector('iframe')) {
			return;
		}
		var frame = document.createElement('iframe');
		frame.src = src;
		frame.title = box.getAttribute('data-title') || 'Карта';
		frame.loading = 'lazy';
		frame.setAttribute('referrerpolicy', 'no-referrer-when-downgrade');
		frame.setAttribute('allowfullscreen', '');
		box.innerHTML = '';
		box.appendChild(frame);
		frame.setAttribute('tabindex', '-1');
		frame.focus({ preventScroll: true });
	}

	document.addEventListener('click', function (event) {
		var button = event.target.closest('.gp-map__facade');
		if (!button) {
			return;
		}
		var box = button.closest('.gp-map');
		if (box) {
			load(box);
		}
	});
})();
