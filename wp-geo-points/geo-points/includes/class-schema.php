<?php
/**
 * JSON-LD для точки.
 *
 * Разметка собирается из тех же полей, которыми набрана видимая страница,
 * — иначе заводится вторая точка правды, и робот Google читает одно,
 * а посетитель видит другое. Именно за такое расхождение снимают
 * расширенный вид сайта целиком.
 *
 * Чего здесь нет и быть не должно: aggregateRating и Review.
 * Google не учитывает отзывы о самом себе, размещённые на своём же сайте
 * (self-serving reviews), а за попытку разметить их звёздами снимает
 * расширенные результаты. Отзывы на странице выводятся для посетителя,
 * а не для разметки.
 */
namespace GeoPoints;

defined('ABSPATH') || defined('GEO_POINTS_TEST') || exit;

class Schema {

	/** Допустимые типы: все — подтипы LocalBusiness. */
	public static function types() {
		return array(
			'Locksmith'                  => 'Locksmith — вскрытие и замена замков',
			'LocalBusiness'              => 'LocalBusiness — общий тип',
			'HomeAndConstructionBusiness'=> 'HomeAndConstructionBusiness — работы на объекте',
			'ProfessionalService'        => 'ProfessionalService — услуги',
		);
	}

	/**
	 * @param array $p точка: title, url, street, locality, region, postal, country,
	 *                 lat, lng, district, hours_spec, place_id, image, intro, metro, streets
	 * @param array $s настройки: org_name, org_url, org_logo, phone_e164, business_type,
	 *                 price_range, currency, same_as
	 */
	public static function location(array $p, array $s) {
		$url  = self::str($p, 'url');
		$type = self::str($s, 'business_type');
		if (!isset(self::types()[$type])) {
			$type = 'Locksmith';
		}

		$node = array(
			'@type'       => $type,
			'@id'         => $url === '' ? null : $url . '#location',
			'name'        => self::str($p, 'title'),
			'url'         => $url === '' ? null : $url,
			'description' => self::str($p, 'intro'),
			'telephone'   => self::str($s, 'phone_e164'),
			'image'       => self::str($p, 'image') === '' ? null : array(self::str($p, 'image')),
			'priceRange'  => self::str($s, 'price_range'),
			'currenciesAccepted' => self::str($s, 'currency'),
		);

		$address = array_filter(
			array(
				'@type'           => 'PostalAddress',
				'streetAddress'   => self::str($p, 'street'),
				'addressLocality' => self::str($p, 'locality'),
				'addressRegion'   => self::str($p, 'region'),
				'postalCode'      => self::str($p, 'postal'),
				'addressCountry'  => self::str($p, 'country') !== '' ? self::str($p, 'country') : 'RU',
			),
			array(__CLASS__, 'filled')
		);
		if (count($address) > 2) {
			$node['address'] = $address;
		}

		$lat = self::str($p, 'lat');
		$lng = self::str($p, 'lng');
		if (is_numeric($lat) && is_numeric($lng)) {
			$node['geo'] = array(
				'@type'     => 'GeoCoordinates',
				'latitude'  => (float) $lat,
				'longitude' => (float) $lng,
			);
		}

		if (!empty($p['hours_spec']) && is_array($p['hours_spec'])) {
			$hours = Hours::to_schema($p['hours_spec']);
			if ($hours) {
				$node['openingHoursSpecification'] = $hours;
			}
		}

		$area = array();
		if (self::str($p, 'district') !== '') {
			$area[] = array('@type' => 'AdministrativeArea', 'name' => self::str($p, 'district'));
		}
		if (self::str($p, 'locality') !== '' && self::str($p, 'locality') !== self::str($p, 'district')) {
			$area[] = array('@type' => 'City', 'name' => self::str($p, 'locality'));
		}
		if ($area) {
			$node['areaServed'] = $area;
		}

		$place_url = Embed::place_url(self::str($p, 'place_id'));
		if ($place_url !== '') {
			$node['hasMap'] = $place_url;
		}

		$same_as = array();
		if ($place_url !== '') {
			$same_as[] = $place_url;
		}
		if (!empty($s['same_as']) && is_array($s['same_as'])) {
			foreach ($s['same_as'] as $link) {
				$link = trim((string) $link);
				if ($link !== '') {
					$same_as[] = $link;
				}
			}
		}
		if ($same_as) {
			$node['sameAs'] = array_values(array_unique($same_as));
		}

		// Девятнадцать точек — это филиалы одной организации, а не девятнадцать
		// разных компаний. Без branchOf Google видит девятнадцать самозванцев
		// с одним телефоном.
		$org_name = self::str($s, 'org_name');
		$org_url  = self::str($s, 'org_url');
		if ($org_name !== '' || $org_url !== '') {
			$branch = array_filter(
				array(
					'@type' => 'Organization',
					'@id'   => $org_url === '' ? null : rtrim($org_url, '/') . '/#organization',
					'name'  => $org_name,
					'url'   => $org_url,
					'logo'  => self::str($s, 'org_logo'),
				),
				array(__CLASS__, 'filled')
			);
			$node['branchOf'] = $branch;
		}

		return array_filter($node, array(__CLASS__, 'filled'));
	}

	/** Готовый граф для вывода в <head>. */
	public static function graph(array $nodes) {
		$nodes = array_values(array_filter($nodes));
		if (!$nodes) {
			return array();
		}
		return array('@context' => 'https://schema.org', '@graph' => $nodes);
	}

	/** Оглавление адресов: ItemList со ссылками на точки. */
	public static function item_list(array $items, $list_url = '') {
		if (!$items) {
			return array();
		}
		$elements = array();
		$i        = 0;
		foreach ($items as $item) {
			$i++;
			$elements[] = array_filter(
				array(
					'@type'    => 'ListItem',
					'position' => $i,
					'name'     => self::str($item, 'title'),
					'url'      => self::str($item, 'url'),
				),
				array(__CLASS__, 'filled')
			);
		}
		return array_filter(
			array(
				'@type'           => 'ItemList',
				'@id'             => $list_url === '' ? null : $list_url . '#locations',
				'itemListElement' => $elements,
			),
			array(__CLASS__, 'filled')
		);
	}

	public static function filled($value) {
		if ($value === null || $value === '' || $value === array()) {
			return false;
		}
		return true;
	}

	private static function str(array $a, $key) {
		return isset($a[$key]) && !is_array($a[$key]) ? trim((string) $a[$key]) : '';
	}
}
