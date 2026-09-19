<?php
/**
 * Телефон. Единый номер на все точки живёт в настройках плагина —
 * поэтому здесь только нормализация и сравнение, без хранения.
 */
namespace GeoPoints;

defined('ABSPATH') || defined('GEO_POINTS_TEST') || exit;

class Phone {

	/** Только цифры. */
	public static function digits($raw) {
		return preg_replace('/\D+/', '', (string) $raw);
	}

	/**
	 * E.164 для tel: и для JSON-LD: +7XXXXXXXXXX.
	 * Российские частности: ведущая 8 -> 7, номер без кода страны -> 7.
	 * Не-российские номера отдаются как есть с плюсом.
	 */
	public static function e164($raw) {
		$d = self::digits($raw);
		if ($d === '') {
			return '';
		}
		if (strlen($d) === 11 && $d[0] === '8') {
			$d = '7' . substr($d, 1);
		} elseif (strlen($d) === 10) {
			$d = '7' . $d;
		}
		return '+' . $d;
	}

	public static function tel_href($raw) {
		$e = self::e164($raw);
		return $e === '' ? '' : 'tel:' . $e;
	}

	/**
	 * Один и тот же номер, записанный по-разному, — это один номер.
	 * Нужно для проверки NAP: в карточке Google и на сайте формат может
	 * отличаться пробелами, но цифры обязаны совпадать.
	 */
	public static function same($a, $b) {
		$ea = self::e164($a);
		$eb = self::e164($b);
		return $ea !== '' && $ea === $eb;
	}

	/** Читаемый вид по умолчанию: +7 (812) 123-45-67. Только для 11-значных RU. */
	public static function pretty_ru($raw) {
		$d = self::digits(self::e164($raw));
		if (strlen($d) !== 11 || $d[0] !== '7') {
			return (string) $raw;
		}
		return sprintf(
			'+7 (%s) %s-%s-%s',
			substr($d, 1, 3), substr($d, 4, 3), substr($d, 7, 2), substr($d, 9, 2)
		);
	}
}
