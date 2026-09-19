<?php
/**
 * Отзывы точки из Google Places API.
 *
 * Ответ кладётся в кэш на 12 часов: без кэша каждый заход посетителя —
 * это платный запрос к Google и лишние полсекунды к ответу страницы.
 * Неудача тоже кэшируется, на час: сломанный ключ не должен превращать
 * каждый просмотр страницы в ожидание таймаута.
 *
 * Разметкой эти отзывы НЕ размечаются — см. class-schema.php.
 */
namespace GeoPoints;

defined('ABSPATH') || exit;

class Reviews {

	const TTL_OK = 12 * HOUR_IN_SECONDS;

	const TTL_FAIL = HOUR_IN_SECONDS;

	public static function fetch($place_id) {
		$place_id = trim((string) $place_id);
		$key      = Settings::get('places_key', '');
		if ($place_id === '' || $key === '') {
			return null;
		}

		$cache_key = 'gp_reviews_' . md5($place_id . '|' . $key);
		$cached    = get_transient($cache_key);
		if ($cached !== false) {
			return is_array($cached) ? $cached : null;
		}

		$response = wp_remote_get(
			'https://places.googleapis.com/v1/places/' . rawurlencode($place_id) . '?languageCode=ru',
			array(
				'timeout' => 8,
				'headers' => array(
					'X-Goog-Api-Key'   => $key,
					'X-Goog-FieldMask' => 'rating,userRatingCount,reviews,googleMapsUri',
				),
			)
		);

		if (is_wp_error($response) || (int) wp_remote_retrieve_response_code($response) !== 200) {
			set_transient($cache_key, 'fail', self::TTL_FAIL);
			return null;
		}

		$body = json_decode(wp_remote_retrieve_body($response), true);
		if (!is_array($body)) {
			set_transient($cache_key, 'fail', self::TTL_FAIL);
			return null;
		}

		$data = self::normalize($body);
		set_transient($cache_key, $data, self::TTL_OK);
		return $data;
	}

	/** Ответ Google -> то, что умеет рисовать шаблон. Вынесено ради тестов. */
	public static function normalize(array $body) {
		$items = array();
		foreach ((array) ($body['reviews'] ?? array()) as $review) {
			$text = '';
			if (isset($review['text']['text'])) {
				$text = (string) $review['text']['text'];
			} elseif (isset($review['originalText']['text'])) {
				$text = (string) $review['originalText']['text'];
			}
			$text = trim($text);
			if ($text === '') {
				continue;
			}
			$items[] = array(
				'author' => (string) ($review['authorAttribution']['displayName'] ?? 'Пользователь Google'),
				'uri'    => (string) ($review['authorAttribution']['uri'] ?? ''),
				'rating' => (int) ($review['rating'] ?? 0),
				'text'   => $text,
				'when'   => (string) ($review['relativePublishTimeDescription'] ?? ''),
			);
		}

		return array(
			'rating' => isset($body['rating']) ? (float) $body['rating'] : 0.0,
			'count'  => isset($body['userRatingCount']) ? (int) $body['userRatingCount'] : 0,
			'map'    => (string) ($body['googleMapsUri'] ?? ''),
			'items'  => $items,
		);
	}

	/** Сброс кэша отзывов — кнопка в «Проверке». */
	public static function flush() {
		global $wpdb;
		$wpdb->query("DELETE FROM {$wpdb->options} WHERE option_name LIKE '_transient_gp_reviews_%' OR option_name LIKE '_transient_timeout_gp_reviews_%'");
	}
}
