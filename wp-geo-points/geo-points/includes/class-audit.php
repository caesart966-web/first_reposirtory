<?php
/**
 * Проверка страниц точек.
 *
 * Главная опасность этого проекта — не незаполненное поле, а девятнадцать
 * почти одинаковых страниц: каждая по отдельности выглядит нормально,
 * а вместе они читаются как дорвеи, и наказание прилетает сайту целиком.
 * Похожесть текстов на глаз не видно, поэтому она меряется.
 *
 * Вторая проверка того же рода — одна и та же карта или один Place ID
 * на нескольких точках. Это следствие копирования кода из соседней
 * карточки, и увидеть это на странице невозможно: карта выглядит картой.
 */
namespace GeoPoints;

defined('ABSPATH') || exit;

class Audit {

	/** Мало текста — это меньше 120 слов: столько занимает один абзац с адресом. */
	const MIN_WORDS = 120;

	/** Ниже этой доли собственного текста страница считается клоном соседней. */
	const MIN_UNIQUE = 0.35;

	public static function init() {
		add_action('admin_menu', array(__CLASS__, 'menu'), 22);
		add_action('admin_notices', array(__CLASS__, 'notice'));
	}

	public static function menu() {
		add_submenu_page(
			'edit.php?post_type=' . Post_Type::TYPE,
			'Проверка точек',
			'Проверка',
			'manage_options',
			'geo-points-audit',
			array(__CLASS__, 'page')
		);
	}

	public static function missing_fields($post_id) {
		$missing = array();
		foreach (Fields::fields() as $key => $field) {
			if (empty($field['required'])) {
				continue;
			}
			if (trim((string) get_post_meta($post_id, '_gp_' . $key, true)) === '') {
				$missing[] = $field['label'];
			}
		}
		return $missing;
	}

	/** Текст страницы целиком — по нему считается похожесть. */
	private static function text($post) {
		return get_post_meta($post->ID, '_gp_intro', true) . ' ' . $post->post_content;
	}

	/**
	 * Слова считаются по Unicode, а не str_word_count(): та работает
	 * побайтно и на кириллице врёт в разы, из-за чего проверка «текста мало»
	 * молча пропускала бы пустые страницы.
	 */
	public static function word_count($text) {
		$normalized = Similarity::normalize($text);
		return $normalized === '' ? 0 : count(explode(' ', $normalized));
	}

	public static function report() {
		$posts = Point::all();
		$texts = array();
		foreach ($posts as $post) {
			$texts[$post->ID] = self::text($post);
		}

		$by_embed = $by_place = $by_street = array();
		foreach ($posts as $post) {
			$embed = get_post_meta($post->ID, '_gp_embed', true);
			$place = get_post_meta($post->ID, '_gp_place_id', true);
			$street= get_post_meta($post->ID, '_gp_street', true);
			if ($embed !== '') {
				$by_embed[$embed][] = $post->ID;
			}
			if ($place !== '') {
				$by_place[$place][] = $post->ID;
			}
			if ($street !== '') {
				$by_street[mb_strtolower($street, 'UTF-8')][] = $post->ID;
			}
		}
		$conflicts = array_flip(Post_Type::conflicting_slugs());

		$rows = array();
		foreach ($posts as $post) {
			$problems = array();
			$warnings = array();

			$missing = self::missing_fields($post->ID);
			if ($missing) {
				$problems[] = 'не заполнено: ' . implode(', ', $missing);
			}

			if (isset($conflicts[$post->post_name])) {
				$problems[] = 'адрес «/' . $post->post_name . '/» занят обычной страницей — точка доступна по служебному адресу, переименуйте одну из них';
			}

			$words = self::word_count($texts[$post->ID]);
			if ($words < self::MIN_WORDS) {
				$warnings[] = sprintf('текста мало: %d слов при минимуме %d', $words, self::MIN_WORDS);
			}

			$others = array();
			foreach ($texts as $id => $text) {
				if ($id !== $post->ID) {
					$others[] = $text;
				}
			}
			$unique = $others ? Similarity::uniqueness($texts[$post->ID], $others) : 1.0;
			if ($others && $unique < self::MIN_UNIQUE) {
				$problems[] = sprintf('собственного текста всего %d%% — страница похожа на соседние', round($unique * 100));
			}

			$twin = '';
			foreach ($posts as $other) {
				if ($other->ID === $post->ID) {
					continue;
				}
				if (Similarity::jaccard($texts[$post->ID], $texts[$other->ID]) >= Similarity::LIMIT) {
					$twin = get_the_title($other);
					break;
				}
			}
			if ($twin !== '') {
				$problems[] = 'текст почти совпадает со страницей «' . $twin . '»';
			}

			// Гео-привязка: в тексте должна встречаться хоть одна своя улица
			// или станция метро, иначе перечисление в полях ничего не даёт.
			$needles = array_merge(
				Csv::to_list(get_post_meta($post->ID, '_gp_metro', true)),
				Csv::to_list(get_post_meta($post->ID, '_gp_streets', true))
			);
			$haystack = Similarity::normalize($texts[$post->ID]);
			$found    = false;
			foreach ($needles as $needle) {
				if ($haystack !== '' && strpos($haystack, Similarity::normalize($needle)) !== false) {
					$found = true;
					break;
				}
			}
			if ($needles && !$found) {
				$warnings[] = 'в тексте не встречается ни одна своя улица или станция метро';
			}

			$embed = get_post_meta($post->ID, '_gp_embed', true);
			if ($embed !== '' && count($by_embed[$embed]) > 1) {
				$problems[] = 'та же карта, что у ' . (count($by_embed[$embed]) - 1) . ' другой точки';
			}
			$place = get_post_meta($post->ID, '_gp_place_id', true);
			if ($place !== '' && count($by_place[$place]) > 1) {
				$problems[] = 'тот же Place ID, что у другой точки — отзывы и кнопка ведут не туда';
			}
			$street = get_post_meta($post->ID, '_gp_street', true);
			if ($street !== '' && count($by_street[mb_strtolower($street, 'UTF-8')]) > 1) {
				$warnings[] = 'адрес совпадает с другой точкой';
			}

			$rows[] = array(
				'id'       => $post->ID,
				'title'    => get_the_title($post),
				'url'      => get_permalink($post),
				'unique'   => $unique,
				'words'    => $words,
				'problems' => $problems,
				'warnings' => $warnings,
			);
		}
		return $rows;
	}

	/** Общие проверки, не привязанные к конкретной точке. */
	public static function global_problems() {
		$out   = array();
		$phone = Settings::get('phone_display', '');
		if ($phone === '') {
			$out[] = 'Не задан единый телефон — он не попадёт ни на одну страницу и ни в одну разметку.';
		} elseif (strlen(Phone::digits($phone)) < 10) {
			$out[] = 'Телефон похож на неполный: ' . $phone;
		}
		if (Settings::get('org_name', '') === '') {
			$out[] = 'Не задано название организации — точки будут выглядеть как несвязанные компании с одним номером.';
		}
		if (!Point::all(1)) {
			$out[] = 'Точек пока нет. Заведите их вручную или импортируйте таблицу.';
		}
		return $out;
	}

	public static function notice() {
		$screen = function_exists('get_current_screen') ? get_current_screen() : null;
		if (!$screen || strpos((string) $screen->id, Post_Type::TYPE) === false) {
			return;
		}
		$conflicts = Post_Type::conflicting_slugs();
		if (!$conflicts) {
			return;
		}
		echo '<div class="notice notice-error"><p><strong>Адреса точек заняты обычными страницами:</strong> /' .
			esc_html(implode('/, /', $conflicts)) . '/. Правило перезаписи для них не ставится — рабочая страница сайта важнее. Переименуйте одну из двух.</p></div>';
	}

	public static function page() {
		if (!current_user_can('manage_options')) {
			return;
		}
		if (isset($_POST['gp_flush_nonce']) && wp_verify_nonce(sanitize_text_field(wp_unslash($_POST['gp_flush_nonce'])), 'gp_flush')) {
			Reviews::flush();
			flush_rewrite_rules(false);
			echo '<div class="notice notice-success"><p>Кэш отзывов очищен, адреса страниц пересобраны.</p></div>';
		}

		$rows   = self::report();
		$global = self::global_problems();
		$bad    = 0;
		foreach ($rows as $row) {
			if ($row['problems']) {
				$bad++;
			}
		}
		?>
		<div class="wrap">
			<h1>Проверка точек</h1>
			<p>Точек: <strong><?php echo count($rows); ?></strong>. С ошибками: <strong><?php echo (int) $bad; ?></strong>.</p>

			<?php foreach ($global as $problem) : ?>
				<div class="notice notice-error"><p><?php echo esc_html($problem); ?></p></div>
			<?php endforeach; ?>

			<table class="widefat striped">
				<thead><tr>
					<th>Точка</th><th>Свой текст</th><th>Слов</th><th>Что не так</th><th>Разметка</th>
				</tr></thead>
				<tbody>
				<?php foreach ($rows as $row) : ?>
					<tr>
						<td>
							<a href="<?php echo esc_url(get_edit_post_link($row['id'])); ?>"><?php echo esc_html($row['title']); ?></a><br>
							<a href="<?php echo esc_url($row['url']); ?>" target="_blank" rel="noopener"><small><?php echo esc_html($row['url']); ?></small></a>
						</td>
						<td<?php echo $row['unique'] < self::MIN_UNIQUE ? ' style="color:#a33;font-weight:600"' : ''; ?>>
							<?php echo esc_html(round($row['unique'] * 100) . '%'); ?>
						</td>
						<td><?php echo (int) $row['words']; ?></td>
						<td>
							<?php if (!$row['problems'] && !$row['warnings']) : ?>
								<span style="color:#127a3d">всё на месте</span>
							<?php else : ?>
								<?php foreach ($row['problems'] as $problem) : ?>
									<div style="color:#a33">✗ <?php echo esc_html($problem); ?></div>
								<?php endforeach; ?>
								<?php foreach ($row['warnings'] as $warning) : ?>
									<div style="color:#8a6d0b">! <?php echo esc_html($warning); ?></div>
								<?php endforeach; ?>
							<?php endif; ?>
						</td>
						<td>
							<a target="_blank" rel="noopener" href="<?php echo esc_url('https://search.google.com/test/rich-results?url=' . rawurlencode($row['url'])); ?>">проверить</a>
						</td>
					</tr>
				<?php endforeach; ?>
				</tbody>
			</table>

			<form method="post" style="margin-top:16px">
				<?php wp_nonce_field('gp_flush', 'gp_flush_nonce'); ?>
				<button class="button" type="submit">Очистить кэш отзывов и пересобрать адреса</button>
			</form>

			<h2>Что проверка не умеет</h2>
			<ul style="list-style:disc;margin-left:20px">
				<li>Сверить адрес на странице с карточкой Google — это делается глазами, один раз, символ в символ.</li>
				<li>Оценить, читается ли текст живым человеком: она меряет непохожесть, а не смысл.</li>
			</ul>
		</div>
		<?php
	}
}
