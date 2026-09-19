<?php
/**
 * Часы работы. Заказчик пишет их одной строкой так, как привык
 * («Пн-Пт 09:00-21:00; Сб,Вс 10:00-18:00» или «круглосуточно»),
 * а плагин разворачивает это и в текст на странице, и в
 * openingHoursSpecification для Google.
 *
 * Одна строка — одна точка правды: расписание на странице и в разметке
 * не могут разойтись, потому что берутся из одного значения.
 */
namespace GeoPoints;

defined('ABSPATH') || defined('GEO_POINTS_TEST') || exit;

class Hours {

	const DAYS = array('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday');

	const SHORT_RU = array('Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс');

	/** Псевдонимы дней: русские и латинские, в нижнем регистре. */
	private static function aliases() {
		return array(
			'пн' => 0, 'пон' => 0, 'понедельник' => 0, 'mo' => 0, 'mon' => 0, 'monday' => 0,
			'вт' => 1, 'вторник' => 1, 'tu' => 1, 'tue' => 1, 'tuesday' => 1,
			'ср' => 2, 'среда' => 2, 'we' => 2, 'wed' => 2, 'wednesday' => 2,
			'чт' => 3, 'четверг' => 3, 'th' => 3, 'thu' => 3, 'thursday' => 3,
			'пт' => 4, 'пятница' => 4, 'fr' => 4, 'fri' => 4, 'friday' => 4,
			'сб' => 5, 'суббота' => 5, 'sa' => 5, 'sat' => 5, 'saturday' => 5,
			'вс' => 6, 'воскресенье' => 6, 'su' => 6, 'sun' => 6, 'sunday' => 6,
		);
	}

	public static function is_always($text) {
		$t = self::lower(trim((string) $text));
		if ($t === '') {
			return false;
		}
		foreach (array('24/7', '24х7', '24x7', 'круглосуточно', 'круглосуточная', 'всегда') as $needle) {
			if (strpos($t, $needle) !== false) {
				return true;
			}
		}
		return false;
	}

	/**
	 * @return array список ['days' => ['Monday', ...], 'opens' => 'HH:MM', 'closes' => 'HH:MM']
	 */
	public static function parse($text) {
		$text = trim((string) $text);
		if ($text === '') {
			return array();
		}
		if (self::is_always($text)) {
			return array(array('days' => self::DAYS, 'opens' => '00:00', 'closes' => '23:59', 'always' => true));
		}

		$out = array();
		$chunks = preg_split('/[;\n\r]+/u', $text);
		foreach ($chunks as $chunk) {
			$chunk = trim($chunk);
			if ($chunk === '') {
				continue;
			}
			if (!preg_match('/(\d{1,2})[:.](\d{2})\s*[-–—]\s*(\d{1,2})[:.](\d{2})/u', $chunk, $t)) {
				continue;
			}
			$opens  = self::time($t[1], $t[2]);
			$closes = self::time($t[3], $t[4]);
			if ($opens === '' || $closes === '') {
				continue;
			}
			$days_part = trim(str_replace($t[0], '', $chunk));
			$days      = self::days($days_part);
			if (!$days) {
				continue;
			}
			$out[] = array('days' => $days, 'opens' => $opens, 'closes' => $closes, 'always' => false);
		}
		return $out;
	}

	/** Дни из куска строки до времени: «Пн-Пт», «Сб,Вс», «ежедневно». */
	public static function days($part) {
		$part = self::lower(trim((string) $part));
		$part = trim($part, " \t.,:-–—");
		if ($part === '' || preg_match('/^(ежедневно|каждый день|daily|all days|без выходных)$/u', $part)) {
			return self::DAYS;
		}

		$aliases = self::aliases();
		$idx     = array();
		foreach (preg_split('/\s*[,]\s*|\s+и\s+/u', $part) as $token) {
			$token = trim($token);
			if ($token === '') {
				continue;
			}
			if (preg_match('/^(.+?)\s*[-–—]\s*(.+)$/u', $token, $m)) {
				$from = isset($aliases[trim($m[1])]) ? $aliases[trim($m[1])] : null;
				$to   = isset($aliases[trim($m[2])]) ? $aliases[trim($m[2])] : null;
				if ($from === null || $to === null) {
					continue;
				}
				$i = $from;
				while (true) {
					$idx[] = $i;
					if ($i === $to) {
						break;
					}
					$i = ($i + 1) % 7;
				}
			} elseif (isset($aliases[$token])) {
				$idx[] = $aliases[$token];
			}
		}
		$idx = array_values(array_unique($idx));
		sort($idx);
		return array_map(function ($i) { return self::DAYS[$i]; }, $idx);
	}

	/** openingHoursSpecification для JSON-LD. */
	public static function to_schema(array $spec) {
		$out = array();
		foreach ($spec as $row) {
			if (empty($row['days'])) {
				continue;
			}
			$out[] = array(
				'@type'     => 'OpeningHoursSpecification',
				'dayOfWeek' => array_map(function ($d) { return 'https://schema.org/' . $d; }, $row['days']),
				'opens'     => $row['opens'],
				'closes'    => $row['closes'],
			);
		}
		return $out;
	}

	/** Обратно в человеческий вид: «Пн–Пт 09:00–21:00, Сб–Вс 10:00–18:00». */
	public static function human(array $spec) {
		if (!$spec) {
			return '';
		}
		if (!empty($spec[0]['always'])) {
			return 'Круглосуточно, без выходных';
		}
		$parts = array();
		foreach ($spec as $row) {
			$parts[] = self::days_label($row['days']) . ' ' . $row['opens'] . '–' . $row['closes'];
		}
		return implode(', ', $parts);
	}

	/** Подряд идущие дни сворачиваются в диапазон: Пн, Вт, Ср -> Пн–Ср. */
	public static function days_label(array $days) {
		$idx = array();
		foreach ($days as $d) {
			$i = array_search($d, self::DAYS, true);
			if ($i !== false) {
				$idx[] = $i;
			}
		}
		sort($idx);
		if (count($idx) === 7) {
			return 'Ежедневно';
		}
		$groups = array();
		$start  = $prev = null;
		foreach ($idx as $i) {
			if ($start === null) {
				$start = $prev = $i;
				continue;
			}
			if ($i === $prev + 1) {
				$prev = $i;
				continue;
			}
			$groups[] = array($start, $prev);
			$start    = $prev = $i;
		}
		if ($start !== null) {
			$groups[] = array($start, $prev);
		}
		$labels = array();
		foreach ($groups as $g) {
			$labels[] = $g[0] === $g[1]
				? self::SHORT_RU[$g[0]]
				: self::SHORT_RU[$g[0]] . '–' . self::SHORT_RU[$g[1]];
		}
		return implode(', ', $labels);
	}

	private static function time($h, $m) {
		$h = (int) $h;
		$m = (int) $m;
		if ($h === 24 && $m === 0) {
			return '23:59';
		}
		if ($h < 0 || $h > 23 || $m < 0 || $m > 59) {
			return '';
		}
		return sprintf('%02d:%02d', $h, $m);
	}

	private static function lower($s) {
		return function_exists('mb_strtolower') ? mb_strtolower($s, 'UTF-8') : strtolower($s);
	}
}
