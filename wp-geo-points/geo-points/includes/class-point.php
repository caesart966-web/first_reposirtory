<?php
/**
 * Точка как набор данных: один источник и для видимой страницы,
 * и для JSON-LD. Разметка не может разойтись с текстом, потому что
 * берётся отсюда же.
 */
namespace GeoPoints;

defined('ABSPATH') || exit;

class Point {

	public static function data($post = null) {
		$post = get_post($post);
		if (!$post || $post->post_type !== Post_Type::TYPE) {
			return array();
		}

		$meta = array();
		foreach (array_keys(Fields::fields()) as $key) {
			$meta[$key] = get_post_meta($post->ID, '_gp_' . $key, true);
		}

		$image = get_the_post_thumbnail_url($post, 'large');

		return array(
			'id'         => $post->ID,
			'title'      => get_the_title($post),
			'url'        => get_permalink($post),
			'intro'      => $meta['intro'] !== '' ? $meta['intro'] : wp_strip_all_tags(get_the_excerpt($post)),
			'street'     => $meta['street'],
			'locality'   => $meta['locality'],
			'region'     => $meta['region'],
			'postal'     => $meta['postal'],
			'country'    => $meta['country'] !== '' ? $meta['country'] : 'RU',
			'district'   => $meta['district'],
			'landmark'   => $meta['landmark'],
			'lat'        => $meta['lat'],
			'lng'        => $meta['lng'],
			'metro'      => Csv::to_list($meta['metro']),
			'streets'    => Csv::to_list($meta['streets']),
			'hours_raw'  => $meta['hours'],
			'hours_spec' => Hours::parse($meta['hours']),
			'embed'      => $meta['embed'],
			'place_id'   => $meta['place_id'],
			'image'      => $image ? $image : '',
		);
	}

	/** Полный адрес одной строкой — для NAP-блока и подписи к карте. */
	public static function address_line(array $p) {
		$parts = array_filter(
			array(
				isset($p['postal']) ? $p['postal'] : '',
				isset($p['locality']) ? $p['locality'] : '',
				isset($p['street']) ? $p['street'] : '',
			),
			'strlen'
		);
		return implode(', ', $parts);
	}

	/** Все опубликованные точки, по алфавиту: любой другой порядок надо обосновывать. */
	public static function all($limit = -1) {
		$posts = get_posts(
			array(
				'post_type'        => Post_Type::TYPE,
				'post_status'      => 'publish',
				'numberposts'      => $limit,
				'orderby'          => 'title',
				'order'            => 'ASC',
				'suppress_filters' => false,
			)
		);
		return $posts;
	}
}
