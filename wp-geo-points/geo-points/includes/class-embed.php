<?php
/**
 * Карта Google: разбор того, что человек скопировал из «Встраивание карт».
 *
 * Плагин НЕ хранит произвольный HTML от пользователя: из вставленного iframe
 * берётся только адрес src, он проверяется на принадлежность Google,
 * а сам тег рисует шаблон. Иначе поле «вставьте код карты» становится
 * дырой для любого стороннего скрипта в админке.
 */
namespace GeoPoints;

defined('ABSPATH') || defined('GEO_POINTS_TEST') || exit;

class Embed {

	const HOSTS = array(
		'www.google.com', 'google.com',
		'maps.google.com', 'www.google.ru', 'google.ru',
		'www.google.com.ua',
	);

	/**
	 * Принимает как целиком <iframe ...>, так и голый адрес.
	 * Возвращает '' , если это не карта Google.
	 */
	public static function extract_src($input) {
		$input = trim((string) $input);
		if ($input === '') {
			return '';
		}
		$src = $input;
		if (stripos($input, '<iframe') !== false) {
			if (!preg_match('/\ssrc\s*=\s*("([^"]*)"|\'([^\']*)\')/i', $input, $m)) {
				return '';
			}
			$src = $m[2] !== '' ? $m[2] : (isset($m[3]) ? $m[3] : '');
		}
		$src = html_entity_decode(trim($src), ENT_QUOTES, 'UTF-8');
		return self::is_valid_src($src) ? $src : '';
	}

	public static function is_valid_src($url) {
		$url = (string) $url;
		$parts = parse_url($url);
		if (!$parts || empty($parts['scheme']) || empty($parts['host']) || empty($parts['path'])) {
			return false;
		}
		if (strtolower($parts['scheme']) !== 'https') {
			return false;
		}
		if (!in_array(strtolower($parts['host']), self::HOSTS, true)) {
			return false;
		}
		return strpos($parts['path'], '/maps/embed') === 0;
	}

	/** Ссылка «оставить отзыв» для конкретной точки. */
	public static function write_review_url($place_id) {
		$place_id = trim((string) $place_id);
		return $place_id === ''
			? ''
			: 'https://search.google.com/local/writereview?placeid=' . rawurlencode($place_id);
	}

	/** Карточка точки на Google Картах — идёт в hasMap и sameAs. */
	public static function place_url($place_id) {
		$place_id = trim((string) $place_id);
		return $place_id === ''
			? ''
			: 'https://www.google.com/maps/place/?q=place_id:' . rawurlencode($place_id);
	}

	/** Place ID иногда уже зашит в скопированную ссылку. */
	public static function place_id_from_url($url) {
		if (preg_match('/place_id[:=]([A-Za-z0-9_\-]{10,})/', (string) $url, $m)) {
			return $m[1];
		}
		return '';
	}
}
