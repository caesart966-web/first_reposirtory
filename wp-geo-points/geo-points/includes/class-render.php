<?php
/**
 * Вывод блоков точки.
 *
 * Карта грузится по клику. Девятнадцать живых iframe Google Карт — это
 * от полумегабайта до полутора на страницу каждый; на телефоне это
 * означает, что посетитель уходит раньше, чем видит адрес. Поэтому
 * сначала рисуется «фасад» — рамка с адресом и кнопкой, а настоящая
 * карта подставляется, когда её попросили.
 */
namespace GeoPoints;

defined('ABSPATH') || exit;

class Render {

	private static $assets_done = false;

	public static function init() {
		add_action('wp_enqueue_scripts', array(__CLASS__, 'register_assets'));
		add_filter('template_include', array(__CLASS__, 'template'));
	}

	public static function register_assets() {
		wp_register_style('geo-points', GEO_POINTS_URL . 'assets/geo-points.css', array(), GEO_POINTS_VERSION);
		wp_register_script('geo-points', GEO_POINTS_URL . 'assets/geo-points.js', array(), GEO_POINTS_VERSION, true);
		if (is_singular(Post_Type::TYPE)) {
			self::assets();
		}
	}

	public static function assets() {
		if (self::$assets_done) {
			return;
		}
		self::$assets_done = true;
		wp_enqueue_style('geo-points');
		wp_enqueue_script('geo-points');
	}

	/** Свой шаблон подставляется, только если тема не предложила свой. */
	public static function template($template) {
		if (!is_singular(Post_Type::TYPE)) {
			return $template;
		}
		$theme = locate_template(array('single-' . Post_Type::TYPE . '.php'));
		if ($theme) {
			return $theme;
		}
		return GEO_POINTS_DIR . 'templates/single-geo_point.php';
	}

	public static function nap(array $p) {
		$phone   = Settings::get('phone_display', '');
		$hours   = Hours::human($p['hours_spec']);
		$address = Point::address_line($p);

		ob_start();
		?>
		<div class="gp-nap">
			<?php if ($address !== '') : ?>
				<p class="gp-nap__row gp-nap__address">
					<span class="gp-nap__label">Адрес</span>
					<span class="gp-nap__value"><?php echo esc_html($address); ?></span>
					<?php if (!empty($p['landmark'])) : ?>
						<span class="gp-nap__note"><?php echo esc_html($p['landmark']); ?></span>
					<?php endif; ?>
				</p>
			<?php endif; ?>

			<?php if ($phone !== '') : ?>
				<p class="gp-nap__row gp-nap__phone">
					<span class="gp-nap__label">Телефон</span>
					<a class="gp-nap__value" href="<?php echo esc_attr(Phone::tel_href($phone)); ?>"><?php echo esc_html($phone); ?></a>
					<span class="gp-nap__note">Единый номер всех мастерских</span>
				</p>
			<?php endif; ?>

			<?php if ($hours !== '') : ?>
				<p class="gp-nap__row">
					<span class="gp-nap__label">Часы работы</span>
					<span class="gp-nap__value"><?php echo esc_html($hours); ?></span>
				</p>
			<?php endif; ?>

			<?php if (!empty($p['metro'])) : ?>
				<p class="gp-nap__row">
					<span class="gp-nap__label">Метро</span>
					<span class="gp-nap__value"><?php echo esc_html(implode(', ', $p['metro'])); ?></span>
				</p>
			<?php endif; ?>
		</div>
		<?php
		return ob_get_clean();
	}

	public static function map(array $p) {
		if (empty($p['embed'])) {
			return '';
		}
		self::assets();
		$title   = sprintf('Карта: %s', $p['title']);
		$address = Point::address_line($p);

		ob_start();
		?>
		<div class="gp-map" data-src="<?php echo esc_url($p['embed']); ?>" data-title="<?php echo esc_attr($title); ?>">
			<button type="button" class="gp-map__facade">
				<span class="gp-map__pin" aria-hidden="true"></span>
				<span class="gp-map__text">
					<strong>Показать карту</strong>
					<?php if ($address !== '') : ?><span><?php echo esc_html($address); ?></span><?php endif; ?>
				</span>
			</button>
			<noscript>
				<iframe src="<?php echo esc_url($p['embed']); ?>" title="<?php echo esc_attr($title); ?>"
					width="100%" height="360" style="border:0" loading="lazy"
					referrerpolicy="no-referrer-when-downgrade"></iframe>
			</noscript>
		</div>
		<?php
		return ob_get_clean();
	}

	public static function reviews(array $p) {
		if (empty($p['place_id']) || !Settings::get('reviews_on', 0)) {
			return '';
		}
		$data = Reviews::fetch($p['place_id']);
		if (!$data || empty($data['items'])) {
			return '';
		}
		$min = (int) Settings::get('reviews_min', 4);

		ob_start();
		echo '<div class="gp-reviews">';
		echo '<h2 class="gp-reviews__title">Отзывы об этой мастерской</h2>';
		if (!empty($data['rating'])) {
			printf(
				'<p class="gp-reviews__summary">%s из 5 по %d отзывам в Google Картах</p>',
				esc_html(number_format_i18n((float) $data['rating'], 1)),
				(int) $data['count']
			);
		}
		echo '<ul class="gp-reviews__list">';
		foreach ($data['items'] as $review) {
			if ((int) $review['rating'] < $min) {
				continue;
			}
			echo '<li class="gp-review">';
			echo '<p class="gp-review__head"><strong>' . esc_html($review['author']) . '</strong>';
			echo '<span class="gp-review__stars" aria-label="' . esc_attr($review['rating'] . ' из 5') . '">' .
				esc_html(str_repeat('★', (int) $review['rating'])) . '</span>';
			if ($review['when'] !== '') {
				echo '<span class="gp-review__when">' . esc_html($review['when']) . '</span>';
			}
			echo '</p>';
			echo '<p class="gp-review__text">' . esc_html($review['text']) . '</p>';
			echo '</li>';
		}
		echo '</ul>';
		echo '<p class="gp-reviews__source">Отзывы загружены из Google Карт.</p>';
		echo '</div>';
		return ob_get_clean();
	}

	public static function cta(array $p) {
		$url = Embed::write_review_url(isset($p['place_id']) ? $p['place_id'] : '');
		if ($url === '') {
			return '';
		}
		$text = Settings::get('cta_text', 'Оставьте отзыв о мастере на Google Картах');
		return sprintf(
			'<a class="gp-cta" href="%s" target="_blank" rel="noopener nofollow">%s</a>',
			esc_url($url),
			esc_html($text)
		);
	}

	/** «Другие адреса» — чтобы страница точки не была тупиком. */
	public static function others(array $p, $limit = 6) {
		$posts = Point::all();
		if (count($posts) < 2) {
			return '';
		}
		$items = array();
		foreach ($posts as $post) {
			if ((int) $post->ID === (int) $p['id']) {
				continue;
			}
			$items[] = $post;
			if (count($items) >= $limit) {
				break;
			}
		}
		if (!$items) {
			return '';
		}
		ob_start();
		echo '<nav class="gp-others" aria-label="Другие адреса"><h2 class="gp-others__title">Другие мастерские</h2><ul>';
		foreach ($items as $post) {
			$district = get_post_meta($post->ID, '_gp_district', true);
			printf(
				'<li><a href="%s">%s</a>%s</li>',
				esc_url(get_permalink($post)),
				esc_html(get_the_title($post)),
				$district !== '' ? '<span>' . esc_html($district) . '</span>' : ''
			);
		}
		echo '</ul></nav>';
		return ob_get_clean();
	}

	/** Оглавление всех адресов — для отдельной страницы «Адреса». */
	public static function list_all() {
		$posts = Point::all();
		if (!$posts) {
			return '';
		}
		self::assets();
		$phone = Settings::get('phone_display', '');
		ob_start();
		echo '<ul class="gp-list">';
		foreach ($posts as $post) {
			$street   = get_post_meta($post->ID, '_gp_street', true);
			$metro    = get_post_meta($post->ID, '_gp_metro', true);
			$district = get_post_meta($post->ID, '_gp_district', true);
			echo '<li class="gp-list__item">';
			printf('<a class="gp-list__link" href="%s">%s</a>', esc_url(get_permalink($post)), esc_html(get_the_title($post)));
			if ($district !== '') {
				echo '<span class="gp-list__district">' . esc_html($district) . '</span>';
			}
			if ($street !== '') {
				echo '<span class="gp-list__address">' . esc_html($street) . '</span>';
			}
			if ($metro !== '') {
				echo '<span class="gp-list__metro">м. ' . esc_html($metro) . '</span>';
			}
			echo '</li>';
		}
		echo '</ul>';
		if ($phone !== '') {
			printf(
				'<p class="gp-list__phone">Единый телефон всех адресов: <a href="%s">%s</a></p>',
				esc_attr(Phone::tel_href($phone)),
				esc_html($phone)
			);
		}
		return ob_get_clean();
	}
}
