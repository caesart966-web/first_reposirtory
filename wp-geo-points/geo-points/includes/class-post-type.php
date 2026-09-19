<?php
/**
 * Тип записи «Точка» и адреса страниц.
 *
 * Корневые адреса (/vskrytie-zamkov-primorsky/) сделаны ТОЧЕЧНЫМИ правилами
 * по реальным слагам, а не общим правилом «^([^/]+)/?$». Общее правило
 * перехватывает вообще все адреса верхнего уровня и роняет остальные
 * страницы сайта — обычные, служебные, чужих плагинов. Девятнадцать точных
 * правил дешевле одного жадного.
 *
 * Слаг, который уже занят страницей или записью, правилом НЕ перекрывается:
 * рабочая страница сайта важнее новой, а расхождение видно в «Проверке».
 */
namespace GeoPoints;

defined('ABSPATH') || exit;

class Post_Type {

	const TYPE = 'geo_point';

	const SLUGS_OPTION = 'geo_points_slugs';

	const HASH_OPTION = 'geo_points_rules_hash';

	const CONFLICTS_OPTION = 'geo_points_conflicts';

	public static function init() {
		add_action('init', array(__CLASS__, 'register'), 5);
		add_action('init', array(__CLASS__, 'rules'), 20);
		add_filter('post_type_link', array(__CLASS__, 'permalink'), 10, 2);

		foreach (array('save_post_' . self::TYPE, 'deleted_post', 'trashed_post', 'untrashed_post') as $hook) {
			add_action($hook, array(__CLASS__, 'refresh_slugs'));
		}

		// Занять адрес точки может и обычная страница, созданная позже,
		// поэтому список конфликтов пересчитывается при сохранении любой записи.
		add_action('save_post', array(__CLASS__, 'refresh_conflicts'), 20);

		add_filter('manage_' . self::TYPE . '_posts_columns', array(__CLASS__, 'columns'));
		add_action('manage_' . self::TYPE . '_posts_custom_column', array(__CLASS__, 'column'), 10, 2);
	}

	public static function register() {
		$mode    = Settings::get('url_mode', 'root');
		$rewrite = $mode === 'prefix'
			? array('slug' => Settings::get('url_prefix', 'adresa'), 'with_front' => false)
			: false;

		register_post_type(
			self::TYPE,
			array(
				'labels'       => array(
					'name'          => 'Точки',
					'singular_name' => 'Точка',
					'add_new'       => 'Добавить точку',
					'add_new_item'  => 'Новая точка',
					'edit_item'     => 'Точка',
					'search_items'  => 'Искать точки',
					'not_found'     => 'Точек пока нет',
					'menu_name'     => 'Точки на картах',
				),
				'public'       => true,
				'has_archive'  => false,
				'menu_icon'    => 'dashicons-location',
				'menu_position'=> 21,
				'supports'     => array('title', 'editor', 'excerpt', 'thumbnail', 'revisions'),
				'show_in_rest' => true,
				'rewrite'      => $rewrite,
				'query_var'    => true,
			)
		);
	}

	/** Слаги опубликованных точек. Кэш в опции — правила строятся на каждом запросе. */
	public static function slugs() {
		$cached = get_option(self::SLUGS_OPTION, null);
		if (is_array($cached)) {
			return $cached;
		}
		return self::refresh_slugs();
	}

	public static function refresh_slugs() {
		global $wpdb;
		$slugs = $wpdb->get_col(
			$wpdb->prepare(
				"SELECT post_name FROM {$wpdb->posts} WHERE post_type = %s AND post_status = 'publish' AND post_name <> ''",
				self::TYPE
			)
		);
		$slugs = array_values(array_unique(array_filter((array) $slugs)));
		update_option(self::SLUGS_OPTION, $slugs, true);
		self::refresh_conflicts();
		return $slugs;
	}

	/**
	 * Слаги, занятые обычными страницами или записями верхнего уровня.
	 *
	 * Ответ лежит в опции: этот список нужен на КАЖДОМ запросе к сайту
	 * (из него строятся правила адресов), а запрос к базе на каждом
	 * просмотре страницы ради девятнадцати строк — плохая цена.
	 */
	public static function conflicting_slugs() {
		$cached = get_option(self::CONFLICTS_OPTION, null);
		if (is_array($cached)) {
			return $cached;
		}
		return self::refresh_conflicts();
	}

	public static function refresh_conflicts() {
		global $wpdb;
		$slugs = get_option(self::SLUGS_OPTION, array());
		$slugs = is_array($slugs) ? $slugs : array();
		if (!$slugs) {
			update_option(self::CONFLICTS_OPTION, array(), true);
			return array();
		}
		$in    = implode(',', array_fill(0, count($slugs), '%s'));
		$found = $wpdb->get_col(
			$wpdb->prepare(
				"SELECT post_name FROM {$wpdb->posts}
				 WHERE post_type IN ('page','post') AND post_status IN ('publish','draft','pending','private')
				 AND post_parent = 0 AND post_name IN ($in)",
				$slugs
			)
		);
		$found = array_values(array_unique((array) $found));
		update_option(self::CONFLICTS_OPTION, $found, true);
		return $found;
	}

	public static function rules() {
		$mode = Settings::get('url_mode', 'root');
		if ($mode !== 'root') {
			self::maybe_flush('prefix:' . Settings::get('url_prefix', 'adresa'));
			return;
		}

		$slugs    = self::slugs();
		$conflict = array_flip(self::conflicting_slugs());
		$used     = array();
		foreach ($slugs as $slug) {
			if (isset($conflict[$slug])) {
				continue;
			}
			add_rewrite_rule(
				'^' . preg_quote($slug, '/') . '/?$',
				'index.php?post_type=' . self::TYPE . '&name=' . $slug,
				'top'
			);
			$used[] = $slug;
		}
		self::maybe_flush('root:' . implode(',', $used));
	}

	/**
	 * Правила перезаписи сбрасываются только когда набор адресов
	 * действительно изменился: flush_rewrite_rules() на каждом запросе —
	 * это перезапись опции с правилами на каждом просмотре страницы.
	 */
	private static function maybe_flush($signature) {
		$hash = md5($signature);
		if (get_option(self::HASH_OPTION) === $hash) {
			return;
		}
		update_option(self::HASH_OPTION, $hash, true);
		flush_rewrite_rules(false);
	}

	public static function permalink($link, $post) {
		if (!$post || get_post_type($post) !== self::TYPE) {
			return $link;
		}
		if (Settings::get('url_mode', 'root') !== 'root') {
			return $link;
		}
		if (in_array(get_post_status($post), array('publish'), true) === false) {
			return $link;
		}
		$conflict = array_flip(self::conflicting_slugs());
		if (isset($conflict[$post->post_name])) {
			return $link;
		}
		return home_url('/' . $post->post_name . '/');
	}

	public static function columns($columns) {
		$out = array();
		foreach ($columns as $key => $label) {
			$out[$key] = $label;
			if ($key === 'title') {
				$out['gp_district'] = 'Район';
				$out['gp_ready']    = 'Готовность';
			}
		}
		return $out;
	}

	public static function column($column, $post_id) {
		if ($column === 'gp_district') {
			echo esc_html(get_post_meta($post_id, '_gp_district', true));
			return;
		}
		if ($column !== 'gp_ready') {
			return;
		}
		$missing = Audit::missing_fields($post_id);
		if (!$missing) {
			echo '<span style="color:#127a3d">готово</span>';
			return;
		}
		echo '<span style="color:#a33">нет: ' . esc_html(implode(', ', array_slice($missing, 0, 3))) . '</span>';
	}
}
