<?php
/**
 * Настройки. Телефон здесь ОДИН на все точки — это не упрощение,
 * а требование NAP: девятнадцать копий номера в девятнадцати карточках
 * расходятся при первой же смене номера, и Google видит девятнадцать
 * разных организаций вместо филиалов одной.
 */
namespace GeoPoints;

defined('ABSPATH') || exit;

class Settings {

	const OPTION = 'geo_points_settings';

	public static function init() {
		add_action('admin_init', array(__CLASS__, 'register'));
		add_action('admin_menu', array(__CLASS__, 'menu'), 20);
	}

	public static function defaults() {
		return array(
			'org_name'      => get_bloginfo('name'),
			'org_url'       => home_url('/'),
			'org_logo'      => '',
			'phone_display' => '',
			'business_type' => 'Locksmith',
			'price_range'   => '₽₽',
			'currency'      => 'RUB',
			'url_mode'      => 'root',
			'url_prefix'    => 'adresa',
			'places_key'    => '',
			'reviews_on'    => 0,
			'reviews_min'   => 4,
			'same_as'       => '',
			'cta_text'      => 'Мы вам помогли? Оставьте отзыв о мастере на Google Картах',
		);
	}

	public static function all() {
		$saved = get_option(self::OPTION, array());
		return array_merge(self::defaults(), is_array($saved) ? $saved : array());
	}

	public static function get($key, $default = '') {
		$all = self::all();
		return array_key_exists($key, $all) && $all[$key] !== '' ? $all[$key] : $default;
	}

	/** Настройки в том виде, в каком их ждёт Schema::location(). */
	public static function for_schema() {
		$all = self::all();
		return array(
			'org_name'      => $all['org_name'],
			'org_url'       => $all['org_url'],
			'org_logo'      => $all['org_logo'],
			'phone_e164'    => Phone::e164($all['phone_display']),
			'business_type' => $all['business_type'],
			'price_range'   => $all['price_range'],
			'currency'      => $all['currency'],
			'same_as'       => array_filter(array_map('trim', preg_split('/[\r\n]+/', (string) $all['same_as']))),
		);
	}

	public static function register() {
		register_setting(
			'geo_points_group',
			self::OPTION,
			array('sanitize_callback' => array(__CLASS__, 'sanitize'))
		);
	}

	public static function sanitize($input) {
		$input = is_array($input) ? $input : array();
		$old   = self::all();
		$out   = self::defaults();

		$out['org_name']      = sanitize_text_field($input['org_name'] ?? '');
		$out['org_url']       = esc_url_raw($input['org_url'] ?? '');
		$out['org_logo']      = esc_url_raw($input['org_logo'] ?? '');
		$out['phone_display'] = sanitize_text_field($input['phone_display'] ?? '');
		$out['business_type'] = isset(Schema::types()[$input['business_type'] ?? '']) ? $input['business_type'] : 'Locksmith';
		$out['price_range']   = sanitize_text_field($input['price_range'] ?? '');
		$out['currency']      = sanitize_text_field($input['currency'] ?? 'RUB');
		$out['url_mode']      = ($input['url_mode'] ?? 'root') === 'prefix' ? 'prefix' : 'root';
		$out['url_prefix']    = sanitize_title($input['url_prefix'] ?? 'adresa');
		$out['places_key']    = sanitize_text_field($input['places_key'] ?? '');
		$out['reviews_on']    = empty($input['reviews_on']) ? 0 : 1;
		$out['reviews_min']   = max(1, min(5, (int) ($input['reviews_min'] ?? 4)));
		$out['same_as']       = sanitize_textarea_field($input['same_as'] ?? '');
		$out['cta_text']      = sanitize_text_field($input['cta_text'] ?? '');

		if ($out['url_prefix'] === '') {
			$out['url_prefix'] = 'adresa';
		}

		// Смена схемы адресов меняет все девятнадцать URL — правила перезаписи
		// обязаны обновиться в тот же заход, иначе страницы отдают 404.
		if ($out['url_mode'] !== $old['url_mode'] || $out['url_prefix'] !== $old['url_prefix']) {
			add_action('shutdown', 'flush_rewrite_rules');
			delete_option('geo_points_rules_hash');
		}

		return $out;
	}

	public static function menu() {
		add_submenu_page(
			'edit.php?post_type=' . Post_Type::TYPE,
			'Настройки гео-точек',
			'Настройки',
			'manage_options',
			'geo-points-settings',
			array(__CLASS__, 'page')
		);
	}

	public static function page() {
		if (!current_user_can('manage_options')) {
			return;
		}
		$s = self::all();
		?>
		<div class="wrap">
			<h1>Настройки гео-точек</h1>
			<form method="post" action="options.php">
				<?php settings_fields('geo_points_group'); ?>
				<h2>Организация</h2>
				<table class="form-table" role="presentation">
					<tr>
						<th scope="row"><label for="gp-org">Название организации</label></th>
						<td><input id="gp-org" class="regular-text" type="text" name="<?php echo esc_attr(self::OPTION); ?>[org_name]" value="<?php echo esc_attr($s['org_name']); ?>">
						<p class="description">Идёт в branchOf: девятнадцать точек — филиалы одной организации, а не девятнадцать компаний с одним телефоном.</p></td>
					</tr>
					<tr>
						<th scope="row"><label for="gp-url">Адрес сайта</label></th>
						<td><input id="gp-url" class="regular-text" type="url" name="<?php echo esc_attr(self::OPTION); ?>[org_url]" value="<?php echo esc_attr($s['org_url']); ?>"></td>
					</tr>
					<tr>
						<th scope="row"><label for="gp-logo">Логотип (URL)</label></th>
						<td><input id="gp-logo" class="regular-text" type="url" name="<?php echo esc_attr(self::OPTION); ?>[org_logo]" value="<?php echo esc_attr($s['org_logo']); ?>"></td>
					</tr>
					<tr>
						<th scope="row"><label for="gp-phone">Телефон (единый)</label></th>
						<td>
							<input id="gp-phone" class="regular-text" type="text" name="<?php echo esc_attr(self::OPTION); ?>[phone_display]" value="<?php echo esc_attr($s['phone_display']); ?>" placeholder="+7 (812) 123-45-67">
							<p class="description">
								Пишется ровно так, как в карточках Google — символ в символ. Для ссылки «позвонить» и для разметки номер приводится сам:
								<code><?php echo esc_html(Phone::e164($s['phone_display'])); ?></code>
							</p>
						</td>
					</tr>
				</table>

				<h2>Разметка</h2>
				<table class="form-table" role="presentation">
					<tr>
						<th scope="row"><label for="gp-type">Тип бизнеса</label></th>
						<td>
							<select id="gp-type" name="<?php echo esc_attr(self::OPTION); ?>[business_type]">
								<?php foreach (Schema::types() as $key => $label) : ?>
									<option value="<?php echo esc_attr($key); ?>" <?php selected($s['business_type'], $key); ?>><?php echo esc_html($label); ?></option>
								<?php endforeach; ?>
							</select>
						</td>
					</tr>
					<tr>
						<th scope="row"><label for="gp-price">Ценовой диапазон</label></th>
						<td><input id="gp-price" type="text" name="<?php echo esc_attr(self::OPTION); ?>[price_range]" value="<?php echo esc_attr($s['price_range']); ?>" size="8"></td>
					</tr>
					<tr>
						<th scope="row"><label for="gp-sameas">Профили организации (sameAs)</label></th>
						<td><textarea id="gp-sameas" class="large-text code" rows="3" name="<?php echo esc_attr(self::OPTION); ?>[same_as]"><?php echo esc_textarea($s['same_as']); ?></textarea>
						<p class="description">По одной ссылке в строке. Карточка точки на Картах добавляется автоматически из её Place ID.</p></td>
					</tr>
				</table>

				<h2>Адреса страниц</h2>
				<table class="form-table" role="presentation">
					<tr>
						<th scope="row">Схема URL</th>
						<td>
							<label><input type="radio" name="<?php echo esc_attr(self::OPTION); ?>[url_mode]" value="root" <?php checked($s['url_mode'], 'root'); ?>> В корне: <code><?php echo esc_html(home_url('/vskrytie-zamkov-primorsky/')); ?></code></label><br>
							<label><input type="radio" name="<?php echo esc_attr(self::OPTION); ?>[url_mode]" value="prefix" <?php checked($s['url_mode'], 'prefix'); ?>> В разделе: <code><?php echo esc_html(home_url('/' . $s['url_prefix'] . '/vskrytie-zamkov-primorsky/')); ?></code></label>
							<p><input type="text" name="<?php echo esc_attr(self::OPTION); ?>[url_prefix]" value="<?php echo esc_attr($s['url_prefix']); ?>" size="12"> — название раздела</p>
							<p class="description">Корневые адреса — как в ТЗ. Раздел — запасной вариант, если тема или другой плагин перехватывает адреса верхнего уровня.</p>
						</td>
					</tr>
				</table>

				<h2>Отзывы</h2>
				<table class="form-table" role="presentation">
					<tr>
						<th scope="row">Показывать отзывы</th>
						<td>
							<label><input type="checkbox" name="<?php echo esc_attr(self::OPTION); ?>[reviews_on]" value="1" <?php checked($s['reviews_on'], 1); ?>> Тянуть отзывы точки из Google Places API</label>
							<p class="description">Отзывы выводятся для посетителя. Размечать их звёздами нельзя: Google не учитывает отзывы о себе на своём же сайте и снимает за это расширенный вид.</p>
						</td>
					</tr>
					<tr>
						<th scope="row"><label for="gp-key">Ключ Google Places API</label></th>
						<td><input id="gp-key" class="regular-text" type="text" name="<?php echo esc_attr(self::OPTION); ?>[places_key]" value="<?php echo esc_attr($s['places_key']); ?>" autocomplete="off">
						<p class="description">Без ключа блок отзывов не выводится вовсе, кнопка «оставить отзыв» работает и без него.</p></td>
					</tr>
					<tr>
						<th scope="row"><label for="gp-min">Не показывать отзывы ниже</label></th>
						<td><input id="gp-min" type="number" min="1" max="5" name="<?php echo esc_attr(self::OPTION); ?>[reviews_min]" value="<?php echo esc_attr($s['reviews_min']); ?>"> звёзд</td>
					</tr>
					<tr>
						<th scope="row"><label for="gp-cta">Текст кнопки отзыва</label></th>
						<td><input id="gp-cta" class="large-text" type="text" name="<?php echo esc_attr(self::OPTION); ?>[cta_text]" value="<?php echo esc_attr($s['cta_text']); ?>"></td>
					</tr>
				</table>
				<?php submit_button(); ?>
			</form>
		</div>
		<?php
	}
}
