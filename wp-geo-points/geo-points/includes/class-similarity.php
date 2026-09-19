<?php
/**
 * Похожесть текстов между точками.
 *
 * Девятнадцать страниц, отличающихся только названием района, Google считает
 * дорвеями и наказывает сайтом целиком. Проверить это на глаз нельзя:
 * страницы открываются по одной и каждая выглядит нормально. Поэтому
 * похожесть меряется — по совпадению цепочек из четырёх слов подряд.
 */
namespace GeoPoints;

defined('ABSPATH') || defined('GEO_POINTS_TEST') || exit;

class Similarity {

	const SHINGLE = 4;

	/** Порог, выше которого страницы считаются клонами друг друга. */
	const LIMIT = 0.55;

	public static function normalize($text) {
		$text = (string) $text;
		$text = preg_replace('/<[^>]*>/u', ' ', $text);
		$text = function_exists('mb_strtolower') ? mb_strtolower($text, 'UTF-8') : strtolower($text);
		$text = preg_replace('/[^\p{L}\p{N}]+/u', ' ', $text);
		return trim(preg_replace('/\s+/u', ' ', $text));
	}

	public static function shingles($text, $n = self::SHINGLE) {
		$words = array_values(array_filter(explode(' ', self::normalize($text)), 'strlen'));
		$out   = array();
		$count = count($words);
		if ($count < $n) {
			return $count ? array(implode(' ', $words)) : array();
		}
		for ($i = 0; $i + $n <= $count; $i++) {
			$out[] = implode(' ', array_slice($words, $i, $n));
		}
		return array_values(array_unique($out));
	}

	/** 0 — ничего общего, 1 — один и тот же текст. */
	public static function jaccard($a, $b) {
		$sa = self::shingles($a);
		$sb = self::shingles($b);
		if (!$sa || !$sb) {
			return 0.0;
		}
		$fa    = array_flip($sa);
		$inter = 0;
		foreach ($sb as $s) {
			if (isset($fa[$s])) {
				$inter++;
			}
		}
		$union = count($sa) + count($sb) - $inter;
		return $union > 0 ? round($inter / $union, 4) : 0.0;
	}

	/**
	 * Доля текста страницы, которой нет ни на одной другой странице набора.
	 * Считается по тем же цепочкам слов.
	 *
	 * @param string   $text   проверяемый текст
	 * @param string[] $others тексты остальных страниц
	 */
	public static function uniqueness($text, array $others) {
		$mine = self::shingles($text);
		if (!$mine) {
			return 0.0;
		}
		$seen = array();
		foreach ($others as $other) {
			foreach (self::shingles($other) as $s) {
				$seen[$s] = true;
			}
		}
		$own = 0;
		foreach ($mine as $s) {
			if (!isset($seen[$s])) {
				$own++;
			}
		}
		return round($own / count($mine), 4);
	}
}
