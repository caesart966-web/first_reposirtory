<?php
/**
 * Что уходит в <head> страницы точки.
 *
 * Title и description плагин выводит, только если на сайте нет SEO-плагина:
 * два тега description на странице — ошибка, которую Google решает сам
 * и обычно не в вашу пользу.
 */
namespace GeoPoints;

defined('ABSPATH') || exit;

class Head {

	public static function init() {
		add_action('wp_head', array(__CLASS__, 'json_ld'), 20);
		add_filter('document_title_parts', array(__CLASS__, 'title'));
		add_action('wp_head', array(__CLASS__, 'description'), 1);
	}

	public static function seo_plugin_active() {
		return defined('RANK_MATH_VERSION')
			|| defined('WPSEO_VERSION')
			|| defined('SEOPRESS_VERSION')
			|| class_exists('All_in_One_SEO_Pack')
			|| defined('AIOSEO_VERSION');
	}

	public static function json_ld() {
		if (!is_singular(Post_Type::TYPE)) {
			return;
		}
		$point = Point::data(get_queried_object_id());
		if (!$point) {
			return;
		}
		$node  = Schema::location($point, Settings::for_schema());
		$graph = Schema::graph(array($node));
		if (!$graph) {
			return;
		}
		echo "\n" . '<script type="application/ld+json">' .
			wp_json_encode($graph, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES) .
			'</script>' . "\n";
	}

	public static function title($parts) {
		if (!is_singular(Post_Type::TYPE) || self::seo_plugin_active()) {
			return $parts;
		}
		$custom = get_post_meta(get_queried_object_id(), '_gp_meta_title', true);
		if ($custom !== '') {
			$parts['title'] = $custom;
		}
		return $parts;
	}

	public static function description() {
		if (!is_singular(Post_Type::TYPE) || self::seo_plugin_active()) {
			return;
		}
		$id   = get_queried_object_id();
		$desc = get_post_meta($id, '_gp_meta_desc', true);
		if ($desc === '') {
			$desc = get_post_meta($id, '_gp_intro', true);
		}
		if ($desc === '') {
			return;
		}
		echo '<meta name="description" content="' . esc_attr(wp_trim_words($desc, 40, '')) . '">' . "\n";
	}
}
