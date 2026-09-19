<?php
/**
 * Plugin Name: Гео-точки (Google Карты)
 * Description: Отдельная страница под каждую точку на Google Картах: единый NAP, микроразметка LocalBusiness/Locksmith, индивидуальная карта, отзывы и кнопка «оставить отзыв». Импорт точек из таблицы, проверка полноты и уникальности страниц.
 * Version: 1.0.0
 * Requires at least: 5.9
 * Requires PHP: 7.4
 * Text Domain: geo-points
 */

defined('ABSPATH') || exit;

define('GEO_POINTS_VERSION', '1.0.0');
define('GEO_POINTS_FILE', __FILE__);
define('GEO_POINTS_DIR', plugin_dir_path(__FILE__));
define('GEO_POINTS_URL', plugin_dir_url(__FILE__));

foreach (
	array(
		'class-phone', 'class-embed', 'class-hours', 'class-schema',
		'class-similarity', 'class-csv', 'class-settings', 'class-post-type',
		'class-fields', 'class-point', 'class-render', 'class-shortcodes',
		'class-reviews', 'class-import', 'class-audit', 'class-head',
	) as $file
) {
	require_once GEO_POINTS_DIR . 'includes/' . $file . '.php';
}

add_action('plugins_loaded', function () {
	GeoPoints\Settings::init();
	GeoPoints\Post_Type::init();
	GeoPoints\Fields::init();
	GeoPoints\Render::init();
	GeoPoints\Shortcodes::init();
	GeoPoints\Head::init();
	GeoPoints\Import::init();
	GeoPoints\Audit::init();
});

register_activation_hook(__FILE__, function () {
	GeoPoints\Post_Type::register();
	GeoPoints\Post_Type::refresh_slugs();
	flush_rewrite_rules();
});

register_deactivation_hook(__FILE__, 'flush_rewrite_rules');
