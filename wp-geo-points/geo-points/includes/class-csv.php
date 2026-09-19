<?php
/**
 * Разбор таблицы с точками.
 *
 * Заказчик ведёт список в Excel, поэтому разделитель может быть любым
 * из трёх, файл — с BOM, а заголовки — на русском. Разбор обязан это
 * пережить: иначе импорт девятнадцати строк превращается в ручной ввод.
 */
namespace GeoPoints;

defined('ABSPATH') || defined('GEO_POINTS_TEST') || exit;

class Csv {

	/** Канонические поля -> как их могли назвать в таблице. */
	public static function aliases() {
		return array(
			'slug'        => array('slug', 'слаг', 'url', 'урл', 'адрес_страницы', 'ссылка'),
			'title'       => array('title', 'h1', 'заголовок', 'название', 'название_точки'),
			'district'    => array('district', 'район', 'округ'),
			'street'      => array('street', 'улица', 'адрес', 'street_address', 'адрес_точки'),
			'locality'    => array('locality', 'city', 'город', 'населённый_пункт', 'населенный_пункт'),
			'region'      => array('region', 'регион', 'субъект', 'область'),
			'postal'      => array('postal', 'postcode', 'zip', 'индекс', 'почтовый_индекс'),
			'country'     => array('country', 'страна', 'код_страны'),
			'lat'         => array('lat', 'latitude', 'широта'),
			'lng'         => array('lng', 'lon', 'longitude', 'долгота'),
			'metro'       => array('metro', 'метро', 'станции_метро', 'станции'),
			'streets'     => array('streets', 'улицы', 'ключевые_улицы'),
			'landmark'    => array('landmark', 'ориентир'),
			'hours'       => array('hours', 'часы', 'часы_работы', 'график', 'режим_работы'),
			'embed'       => array('embed', 'карта', 'map', 'iframe', 'код_карты'),
			'place_id'    => array('place_id', 'placeid', 'id_точки', 'google_place_id'),
			'intro'       => array('intro', 'лид', 'вступление', 'подзаголовок'),
			'content'     => array('content', 'текст', 'описание', 'контент'),
			'meta_title'  => array('meta_title', 'title_tag', 'мета_заголовок', 'seo_title'),
			'meta_desc'   => array('meta_desc', 'meta_description', 'описание_seo', 'seo_description', 'мета_описание'),
		);
	}

	public static function canonical_key($header) {
		$h = trim((string) $header);
		$h = preg_replace('/^\xEF\xBB\xBF/', '', $h);
		$h = function_exists('mb_strtolower') ? mb_strtolower($h, 'UTF-8') : strtolower($h);
		$h = trim(preg_replace('/\s+/u', '_', $h), " _\t");
		$h = str_replace('ё', 'е', $h);
		foreach (self::aliases() as $key => $names) {
			foreach ($names as $name) {
				if ($h === str_replace('ё', 'е', $name)) {
					return $key;
				}
			}
		}
		return '';
	}

	public static function detect_delimiter($line) {
		$best  = ',';
		$count = 0;
		foreach (array(',', ';', "\t") as $d) {
			$n = substr_count($line, $d);
			if ($n > $count) {
				$count = $n;
				$best  = $d;
			}
		}
		return $best;
	}

	/**
	 * @return array ['rows' => [...], 'errors' => [...], 'unknown' => [...]]
	 */
	public static function parse($content) {
		$content = (string) $content;
		$content = preg_replace('/^\xEF\xBB\xBF/', '', $content);
		$content = str_replace("\r\n", "\n", $content);
		if (trim($content) === '') {
			return array('rows' => array(), 'errors' => array('Файл пуст.'), 'unknown' => array());
		}

		$first     = strtok($content, "\n");
		$delimiter = self::detect_delimiter($first);

		$fh = fopen('php://temp', 'r+');
		fwrite($fh, $content);
		rewind($fh);

		$header = fgetcsv($fh, 0, $delimiter);
		if (!$header) {
			fclose($fh);
			return array('rows' => array(), 'errors' => array('Не читается строка заголовков.'), 'unknown' => array());
		}

		$map     = array();
		$unknown = array();
		foreach ($header as $i => $name) {
			$key = self::canonical_key($name);
			if ($key === '') {
				if (trim((string) $name) !== '') {
					$unknown[] = trim((string) $name);
				}
				continue;
			}
			$map[$i] = $key;
		}

		$errors = array();
		if (!in_array('slug', $map, true) && !in_array('title', $map, true)) {
			$errors[] = 'В таблице нет ни столбца «slug», ни «title» — строки не с чем связать.';
		}

		$rows = array();
		$line = 1;
		while (($data = fgetcsv($fh, 0, $delimiter)) !== false) {
			$line++;
			if ($data === array(null) || (count($data) === 1 && trim((string) $data[0]) === '')) {
				continue;
			}
			$row = array('_line' => $line);
			foreach ($map as $i => $key) {
				$row[$key] = isset($data[$i]) ? trim((string) $data[$i]) : '';
			}
			if (self::is_empty_row($row)) {
				continue;
			}
			$rows[] = $row;
		}
		fclose($fh);

		return array('rows' => $rows, 'errors' => $errors, 'unknown' => $unknown);
	}

	private static function is_empty_row(array $row) {
		foreach ($row as $key => $value) {
			if ($key !== '_line' && $value !== '') {
				return false;
			}
		}
		return true;
	}

	/** Список через запятую -> массив. Метро и улицы вводятся именно так. */
	public static function to_list($value) {
		$parts = preg_split('/\s*[,;|]\s*/u', (string) $value);
		$out   = array();
		foreach ($parts as $p) {
			$p = trim($p);
			if ($p !== '') {
				$out[] = $p;
			}
		}
		return array_values(array_unique($out));
	}
}
