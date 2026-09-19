<?php
/**
 * Шорткоды: те же блоки, но доступные из любого редактора и конструктора.
 * Нужны, чтобы страницу точки можно было собрать и не нашим шаблоном.
 */
namespace GeoPoints;

defined('ABSPATH') || exit;

class Shortcodes {

	public static function init() {
		add_shortcode('geo_nap', array(__CLASS__, 'nap'));
		add_shortcode('geo_map', array(__CLASS__, 'map'));
		add_shortcode('geo_reviews', array(__CLASS__, 'reviews'));
		add_shortcode('geo_review_button', array(__CLASS__, 'cta'));
		add_shortcode('geo_points_list', array(__CLASS__, 'list_all'));
	}

	/** Точка из атрибута point="slug|ID", иначе — текущая. */
	private static function point($atts) {
		$atts = shortcode_atts(array('point' => ''), $atts);
		if ($atts['point'] === '') {
			return Point::data(get_queried_object_id());
		}
		$post = is_numeric($atts['point'])
			? get_post((int) $atts['point'])
			: get_page_by_path(sanitize_title($atts['point']), OBJECT, Post_Type::TYPE);
		return $post ? Point::data($post) : array();
	}

	public static function nap($atts) {
		$p = self::point($atts);
		if (!$p) {
			return '';
		}
		Render::assets();
		return Render::nap($p);
	}

	public static function map($atts) {
		$p = self::point($atts);
		return $p ? Render::map($p) : '';
	}

	public static function reviews($atts) {
		$p = self::point($atts);
		if (!$p) {
			return '';
		}
		Render::assets();
		return Render::reviews($p);
	}

	public static function cta($atts) {
		$p = self::point($atts);
		if (!$p) {
			return '';
		}
		Render::assets();
		return Render::cta($p);
	}

	public static function list_all() {
		return Render::list_all();
	}
}
