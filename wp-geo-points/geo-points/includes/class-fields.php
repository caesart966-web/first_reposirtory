<?php
/**
 * Поля точки: один список, из которого растут форма в админке,
 * импорт из таблицы, проверка полноты и вывод на страницу.
 * Новое поле добавляется здесь и появляется везде разом.
 */
namespace GeoPoints;

defined('ABSPATH') || exit;

class Fields {

	public static function fields() {
		return array(
			'district'   => array('label' => 'Район / округ', 'type' => 'text', 'required' => true,
				'hint' => 'Приморский район. Идёт в H1, в areaServed и в оглавление адресов.'),
			'street'     => array('label' => 'Улица и дом', 'type' => 'text', 'required' => true,
				'hint' => 'Символ в символ как в карточке Google: «Богатырский пр., 12, корп. 1».'),
			'locality'   => array('label' => 'Город', 'type' => 'text', 'required' => true),
			'region'     => array('label' => 'Регион / субъект', 'type' => 'text', 'required' => false),
			'postal'     => array('label' => 'Почтовый индекс', 'type' => 'text', 'required' => false),
			'country'    => array('label' => 'Код страны', 'type' => 'text', 'required' => false, 'default' => 'RU'),
			'landmark'   => array('label' => 'Ориентир', 'type' => 'text', 'required' => false,
				'hint' => 'Вход со двора, напротив сбербанка — то, что помогает человеку дойти.'),
			'lat'        => array('label' => 'Широта', 'type' => 'text', 'required' => false),
			'lng'        => array('label' => 'Долгота', 'type' => 'text', 'required' => false),
			'metro'      => array('label' => 'Станции метро', 'type' => 'text', 'required' => true,
				'hint' => 'Через запятую. Выводятся на странице и дают гео-привязку.'),
			'streets'    => array('label' => 'Ключевые улицы', 'type' => 'text', 'required' => true,
				'hint' => 'Через запятую: улицы и кварталы, которые обслуживает эта точка.'),
			'hours'      => array('label' => 'Часы работы', 'type' => 'text', 'required' => true,
				'hint' => '«круглосуточно» или «Пн-Пт 09:00-21:00; Сб,Вс 10:00-18:00».'),
			'embed'      => array('label' => 'Код карты Google', 'type' => 'textarea', 'required' => true,
				'hint' => 'Google Карты → точка → «Поделиться» → «Встраивание карт» → скопировать HTML. Сохранится только адрес карты, сам код тега плагин соберёт сам.'),
			'place_id'   => array('label' => 'Place ID точки', 'type' => 'text', 'required' => true,
				'hint' => 'Нужен для кнопки «оставить отзыв» и для ссылки на карточку. Ищется в Google Place ID Finder.'),
			'intro'      => array('label' => 'Короткое описание', 'type' => 'textarea', 'required' => false,
				'hint' => 'Одно-два предложения под заголовком. Идёт в description разметки.'),
			'meta_title' => array('label' => 'Title для поиска', 'type' => 'text', 'required' => false,
				'hint' => 'Если пусто — берётся заголовок страницы. Не выводится, когда активен Rank Math или Yoast.'),
			'meta_desc'  => array('label' => 'Description для поиска', 'type' => 'textarea', 'required' => false),
		);
	}

	public static function init() {
		add_action('add_meta_boxes', array(__CLASS__, 'box'));
		add_action('save_post_' . Post_Type::TYPE, array(__CLASS__, 'save'), 10, 2);
	}

	public static function box() {
		add_meta_box(
			'geo-point-fields',
			'Данные точки (NAP, карта, отзывы)',
			array(__CLASS__, 'render'),
			Post_Type::TYPE,
			'normal',
			'high'
		);
	}

	public static function render($post) {
		wp_nonce_field('geo_point_save', 'geo_point_nonce');
		$phone = Settings::get('phone_display', '');
		echo '<p style="margin:0 0 12px"><strong>Телефон:</strong> ' . esc_html($phone !== '' ? $phone : 'не задан') .
			' — общий для всех точек, меняется в «Точки на картах → Настройки».</p>';
		echo '<table class="form-table" role="presentation">';
		foreach (self::fields() as $key => $field) {
			$value = get_post_meta($post->ID, '_gp_' . $key, true);
			if ($value === '' && isset($field['default'])) {
				$value = $field['default'];
			}
			$id = 'gp-' . $key;
			echo '<tr><th scope="row"><label for="' . esc_attr($id) . '">' . esc_html($field['label']);
			if (!empty($field['required'])) {
				echo ' <span style="color:#a33">*</span>';
			}
			echo '</label></th><td>';
			if ($field['type'] === 'textarea') {
				echo '<textarea class="large-text" rows="3" id="' . esc_attr($id) . '" name="gp[' . esc_attr($key) . ']">' . esc_textarea($value) . '</textarea>';
			} else {
				echo '<input class="regular-text" type="text" id="' . esc_attr($id) . '" name="gp[' . esc_attr($key) . ']" value="' . esc_attr($value) . '">';
			}
			if (!empty($field['hint'])) {
				echo '<p class="description">' . esc_html($field['hint']) . '</p>';
			}
			echo '</td></tr>';
		}
		echo '</table>';
	}

	public static function save($post_id, $post) {
		if (!isset($_POST['geo_point_nonce']) || !wp_verify_nonce(sanitize_text_field(wp_unslash($_POST['geo_point_nonce'])), 'geo_point_save')) {
			return;
		}
		if (defined('DOING_AUTOSAVE') && DOING_AUTOSAVE) {
			return;
		}
		if (!current_user_can('edit_post', $post_id)) {
			return;
		}
		$input = isset($_POST['gp']) && is_array($_POST['gp']) ? wp_unslash($_POST['gp']) : array();
		self::save_values($post_id, $input);
	}

	/** Общая точка сохранения: ею же пользуется импорт из таблицы. */
	public static function save_values($post_id, array $input) {
		foreach (self::fields() as $key => $field) {
			if (!array_key_exists($key, $input)) {
				continue;
			}
			$value = $input[$key];
			if ($key === 'embed') {
				$value = Embed::extract_src($value);
			} elseif ($key === 'place_id') {
				$value = sanitize_text_field($value);
			} elseif ($field['type'] === 'textarea') {
				$value = sanitize_textarea_field($value);
			} else {
				$value = sanitize_text_field($value);
			}
			update_post_meta($post_id, '_gp_' . $key, $value);
		}

		// Place ID часто уже зашит в скопированную ссылку — не заставляем
		// искать его руками девятнадцать раз.
		if (get_post_meta($post_id, '_gp_place_id', true) === '') {
			$from_url = Embed::place_id_from_url(get_post_meta($post_id, '_gp_embed', true));
			if ($from_url !== '') {
				update_post_meta($post_id, '_gp_place_id', $from_url);
			}
		}
	}
}
