<?php
/**
 * Импорт точек из таблицы.
 *
 * Девятнадцать страниц, заведённых руками, — это девятнадцать поводов
 * ошибиться в адресе и сутки работы. Таблица заливается один раз, и её же
 * можно перезалить после правок: связь идёт по слагу, поэтому повторный
 * импорт обновляет, а не плодит.
 */
namespace GeoPoints;

defined('ABSPATH') || exit;

class Import {

	public static function init() {
		add_action('admin_menu', array(__CLASS__, 'menu'), 21);
	}

	public static function menu() {
		add_submenu_page(
			'edit.php?post_type=' . Post_Type::TYPE,
			'Импорт точек',
			'Импорт из таблицы',
			'manage_options',
			'geo-points-import',
			array(__CLASS__, 'page')
		);
	}

	/** Слаг из значения: принимает и слаг, и целый URL. */
	public static function slug_from($value, $fallback = '') {
		$value = trim((string) $value);
		if ($value === '') {
			return sanitize_title($fallback);
		}
		if (preg_match('#^https?://#i', $value)) {
			$path  = (string) parse_url($value, PHP_URL_PATH);
			$parts = array_values(array_filter(explode('/', $path), 'strlen'));
			$value = $parts ? end($parts) : '';
		}
		return sanitize_title(trim($value, '/'));
	}

	/**
	 * Разбор строк в задания на импорт. Без обращения к базе, кроме поиска
	 * существующей точки, — чтобы предпросмотр показывал ровно то,
	 * что потом произойдёт.
	 */
	public static function plan(array $rows) {
		$plan  = array();
		$seen  = array();
		foreach ($rows as $row) {
			$title = trim((string) ($row['title'] ?? ''));
			$slug  = self::slug_from($row['slug'] ?? '', $title);
			$notes = array();

			if ($slug === '') {
				$notes[] = 'нет ни адреса страницы, ни заголовка — строка пропущена';
				$plan[]  = array('slug' => '', 'title' => $title, 'action' => 'skip', 'notes' => $notes, 'row' => $row);
				continue;
			}
			if (isset($seen[$slug])) {
				$notes[] = 'такой адрес уже был в строке ' . $seen[$slug] . ' — строка пропущена';
				$plan[]  = array('slug' => $slug, 'title' => $title, 'action' => 'skip', 'notes' => $notes, 'row' => $row);
				continue;
			}
			$seen[$slug] = $row['_line'] ?? '?';

			$existing = get_page_by_path($slug, OBJECT, Post_Type::TYPE);
			$missing  = array();
			foreach (Fields::fields() as $key => $field) {
				if (!empty($field['required']) && trim((string) ($row[$key] ?? '')) === '') {
					$missing[] = $field['label'];
				}
			}
			if ($missing) {
				$notes[] = 'не заполнено: ' . implode(', ', $missing);
			}
			if (!empty($row['embed']) && Embed::extract_src($row['embed']) === '') {
				$notes[] = 'код карты не похож на карту Google — поле не сохранится';
			}

			$plan[] = array(
				'slug'   => $slug,
				'title'  => $title !== '' ? $title : $slug,
				'action' => $existing ? 'update' : 'create',
				'id'     => $existing ? (int) $existing->ID : 0,
				'notes'  => $notes,
				'row'    => $row,
			);
		}
		return $plan;
	}

	public static function apply(array $plan, $publish = true) {
		$created = $updated = $skipped = 0;
		foreach ($plan as $task) {
			if ($task['action'] === 'skip') {
				$skipped++;
				continue;
			}
			$row  = $task['row'];
			$args = array(
				'post_type'    => Post_Type::TYPE,
				'post_title'   => $task['title'],
				'post_name'    => $task['slug'],
				'post_status'  => $publish ? 'publish' : 'draft',
				'post_content' => (string) ($row['content'] ?? ''),
				'post_excerpt' => (string) ($row['intro'] ?? ''),
			);
			if ($task['action'] === 'update') {
				$args['ID'] = $task['id'];
				// Пустая ячейка в таблице не должна стирать уже написанный текст:
				// контент часто правят на сайте, а таблицу ведут только под адреса.
				if (trim($args['post_content']) === '') {
					unset($args['post_content']);
				}
				if (trim($args['post_excerpt']) === '') {
					unset($args['post_excerpt']);
				}
				$id = wp_update_post($args, true);
				$updated++;
			} else {
				$id = wp_insert_post($args, true);
				$created++;
			}
			if (is_wp_error($id) || !$id) {
				continue;
			}
			$values = array();
			foreach (array_keys(Fields::fields()) as $key) {
				if (array_key_exists($key, $row) && trim((string) $row[$key]) !== '') {
					$values[$key] = $row[$key];
				}
			}
			Fields::save_values((int) $id, $values);
		}
		Post_Type::refresh_slugs();
		delete_option(Post_Type::HASH_OPTION);
		return compact('created', 'updated', 'skipped');
	}

	public static function page() {
		if (!current_user_can('manage_options')) {
			return;
		}

		$content = '';
		$plan    = array();
		$parsed  = array('rows' => array(), 'errors' => array(), 'unknown' => array());
		$done    = null;

		if (isset($_POST['gp_import_nonce']) && wp_verify_nonce(sanitize_text_field(wp_unslash($_POST['gp_import_nonce'])), 'gp_import')) {
			if (!empty($_FILES['gp_file']['tmp_name']) && is_uploaded_file($_FILES['gp_file']['tmp_name'])) {
				$content = (string) file_get_contents($_FILES['gp_file']['tmp_name']);
			} elseif (isset($_POST['gp_csv'])) {
				$content = (string) wp_unslash($_POST['gp_csv']);
			}
			if (trim($content) !== '') {
				$parsed = Csv::parse($content);
				$plan   = self::plan($parsed['rows']);
				if (isset($_POST['gp_apply'])) {
					$done = self::apply($plan, !empty($_POST['gp_publish']));
				}
			}
		}
		?>
		<div class="wrap">
			<h1>Импорт точек из таблицы</h1>

			<?php if ($done) : ?>
				<div class="notice notice-success"><p>
					Создано: <strong><?php echo (int) $done['created']; ?></strong>,
					обновлено: <strong><?php echo (int) $done['updated']; ?></strong>,
					пропущено: <strong><?php echo (int) $done['skipped']; ?></strong>.
					Дальше — <a href="<?php echo esc_url(admin_url('edit.php?post_type=' . Post_Type::TYPE . '&page=geo-points-audit')); ?>">проверка страниц</a>.
				</p></div>
			<?php endif; ?>

			<?php foreach ($parsed['errors'] as $error) : ?>
				<div class="notice notice-error"><p><?php echo esc_html($error); ?></p></div>
			<?php endforeach; ?>

			<?php if ($parsed['unknown']) : ?>
				<div class="notice notice-warning"><p>Столбцы, которые плагин не узнал (они не импортируются):
					<code><?php echo implode('</code>, <code>', array_map('esc_html', $parsed['unknown'])); ?></code></p></div>
			<?php endif; ?>

			<form method="post" enctype="multipart/form-data">
				<?php wp_nonce_field('gp_import', 'gp_import_nonce'); ?>
				<p><label><strong>Файл CSV</strong> <input type="file" name="gp_file" accept=".csv,text/csv,text/plain"></label></p>
				<p>или вставьте таблицу сюда:</p>
				<textarea class="large-text code" rows="8" name="gp_csv" placeholder="slug;title;district;street;locality;metro;streets;hours;embed;place_id"><?php echo esc_textarea($content); ?></textarea>
				<p>
					<label><input type="checkbox" name="gp_publish" value="1" checked> сразу публиковать</label>
				</p>
				<p>
					<button class="button button-secondary" type="submit">Показать, что получится</button>
					<?php if ($plan) : ?>
						<button class="button button-primary" type="submit" name="gp_apply" value="1">Импортировать <?php echo (int) count($plan); ?> строк</button>
					<?php endif; ?>
				</p>
			</form>

			<?php if ($plan) : ?>
				<h2>Предпросмотр</h2>
				<table class="widefat striped">
					<thead><tr><th>Адрес страницы</th><th>Заголовок</th><th>Действие</th><th>Замечания</th></tr></thead>
					<tbody>
					<?php foreach ($plan as $task) : ?>
						<tr>
							<td><code><?php echo esc_html($task['slug']); ?></code></td>
							<td><?php echo esc_html($task['title']); ?></td>
							<td><?php
								echo esc_html(
									$task['action'] === 'create' ? 'создать' : ($task['action'] === 'update' ? 'обновить' : 'пропустить')
								);
							?></td>
							<td><?php echo $task['notes'] ? esc_html(implode('; ', $task['notes'])) : '—'; ?></td>
						</tr>
					<?php endforeach; ?>
					</tbody>
				</table>
			<?php endif; ?>

			<h2>Какие столбцы понимает импорт</h2>
			<p>Названия можно писать по-русски или по-английски, порядок любой, лишние столбцы игнорируются.</p>
			<table class="widefat striped">
				<thead><tr><th>Поле</th><th>Как можно назвать столбец</th></tr></thead>
				<tbody>
				<?php foreach (Csv::aliases() as $key => $names) : ?>
					<tr><td><code><?php echo esc_html($key); ?></code></td><td><?php echo esc_html(implode(', ', $names)); ?></td></tr>
				<?php endforeach; ?>
				</tbody>
			</table>
		</div>
		<?php
	}
}
