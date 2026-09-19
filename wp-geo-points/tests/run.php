<?php
/**
 * Проверки плагина без WordPress.
 *
 * Здесь проверяется то, что ломается молча: разбор часов, чистка кода карты,
 * телефон в разных записях, сборка JSON-LD и похожесть страниц. Всё это
 * не даёт белого экрана при поломке — оно просто начинает выдавать
 * неправильный ответ, а на сайте это видно только через выдачу.
 *
 * Запуск: php tests/run.php
 */

define('GEO_POINTS_TEST', true);
define('ABSPATH', __DIR__ . '/');
define('HOUR_IN_SECONDS', 3600);

// Заглушки WordPress: ровно те, что нужны проверяемым методам.
if (!function_exists('sanitize_title')) {
	function sanitize_title($title) {
		$title = function_exists('mb_strtolower') ? mb_strtolower((string) $title, 'UTF-8') : strtolower((string) $title);
		$title = preg_replace('/[^a-z0-9а-яё\-_ ]+/u', '', $title);
		$title = preg_replace('/[\s_]+/u', '-', trim($title));
		return trim(preg_replace('/-+/', '-', $title), '-');
	}
}
if (!function_exists('esc_html')) { function esc_html($t) { return htmlspecialchars((string) $t, ENT_QUOTES, 'UTF-8'); } }
if (!function_exists('esc_attr')) { function esc_attr($t) { return esc_html($t); } }

$base = dirname(__DIR__) . '/geo-points/includes/';
foreach (array('class-phone', 'class-embed', 'class-hours', 'class-schema', 'class-similarity', 'class-csv', 'class-fields', 'class-import', 'class-reviews') as $file) {
	require_once $base . $file . '.php';
}

use GeoPoints\Phone;
use GeoPoints\Embed;
use GeoPoints\Hours;
use GeoPoints\Schema;
use GeoPoints\Similarity;
use GeoPoints\Csv;
use GeoPoints\Fields;
use GeoPoints\Import;
use GeoPoints\Reviews;

$passed = 0;
$failed = array();

function check($name, $actual, $expected) {
	global $passed, $failed;
	if ($actual === $expected) {
		$passed++;
		return;
	}
	$failed[] = sprintf(
		"%s\n    ожидалось: %s\n    получено:  %s",
		$name,
		var_export($expected, true),
		var_export($actual, true)
	);
}

function ok($name, $condition) {
	check($name, (bool) $condition, true);
}

/* ---------------------------------------------------------------- телефон */

check('телефон: 8 -> +7', Phone::e164('8 (812) 123-45-67'), '+78121234567');
check('телефон: уже международный', Phone::e164('+7 812 123 45 67'), '+78121234567');
check('телефон: без кода страны', Phone::e164('812 123-45-67'), '+78121234567');
check('телефон: пустой остаётся пустым', Phone::e164(''), '');
ok('телефон: одинаковые цифры — один номер', Phone::same('+7 (812) 123-45-67', '8812 1234567'));
ok('телефон: разные номера не равны', !Phone::same('+7 (812) 123-45-67', '+7 (812) 123-45-68'));
check('телефон: читаемый вид', Phone::pretty_ru('88121234567'), '+7 (812) 123-45-67');

/* ------------------------------------------------------------------ карта */

$iframe = '<iframe src="https://www.google.com/maps/embed?pb=!1m18!1m12" width="600" height="450" style="border:0"></iframe>';
check('карта: src из iframe', Embed::extract_src($iframe), 'https://www.google.com/maps/embed?pb=!1m18!1m12');
check(
	'карта: одинарные кавычки',
	Embed::extract_src("<iframe src='https://www.google.com/maps/embed?pb=1'></iframe>"),
	'https://www.google.com/maps/embed?pb=1'
);
check('карта: голый адрес', Embed::extract_src('https://www.google.com/maps/embed?pb=1'), 'https://www.google.com/maps/embed?pb=1');
check('карта: чужой домен отвергается', Embed::extract_src('<iframe src="https://evil.example/maps/embed?pb=1"></iframe>'), '');
check('карта: http отвергается', Embed::extract_src('http://www.google.com/maps/embed?pb=1'), '');
check('карта: не /maps/embed отвергается', Embed::extract_src('https://www.google.com/search?q=1'), '');
check('карта: пустое поле', Embed::extract_src(''), '');
check(
	'карта: ссылка на отзыв',
	Embed::write_review_url('ChIJ_abc-123'),
	'https://search.google.com/local/writereview?placeid=ChIJ_abc-123'
);
check('карта: Place ID из ссылки', Embed::place_id_from_url('https://www.google.com/maps/place/?q=place_id:ChIJ_abc-123'), 'ChIJ_abc-123');

/* -------------------------------------------------------------------- часы */

ok('часы: круглосуточно распознаётся', Hours::is_always('Круглосуточно, без выходных'));
ok('часы: 24/7 распознаётся', Hours::is_always('24/7'));
ok('часы: обычный график — не круглосуточно', !Hours::is_always('Пн-Пт 09:00-21:00'));

$spec = Hours::parse('Пн-Пт 09:00-21:00; Сб,Вс 10:00-18:00');
check('часы: два интервала', count($spec), 2);
check('часы: будни', $spec[0]['days'], array('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'));
check('часы: открытие', $spec[0]['opens'], '09:00');
check('часы: выходные', $spec[1]['days'], array('Saturday', 'Sunday'));
check('часы: человеческий вид', Hours::human($spec), 'Пн–Пт 09:00–21:00, Сб–Вс 10:00–18:00');

$always = Hours::parse('круглосуточно');
check('часы: круглосуточно — все семь дней', count($always[0]['days']), 7);
check('часы: круглосуточно — до 23:59', $always[0]['closes'], '23:59');
check('часы: круглосуточно — подпись', Hours::human($always), 'Круглосуточно, без выходных');

check('часы: ежедневно', Hours::parse('Ежедневно 10:00-20:00')[0]['days'], Hours::DAYS);
check('часы: латиницей', Hours::parse('Mo-Fr 09:00-18:00')[0]['days'], array('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'));
check('часы: 24:00 приводится к 23:59', Hours::parse('Пн 09:00-24:00')[0]['closes'], '23:59');
check('часы: мусор не ломает разбор', Hours::parse('как договоримся'), array());
check('часы: переход через воскресенье', Hours::parse('Сб-Вт 10:00-18:00')[0]['days'], array('Monday', 'Tuesday', 'Saturday', 'Sunday'));

$schema_hours = Hours::to_schema($spec);
check('часы: формат для разметки', $schema_hours[0]['@type'], 'OpeningHoursSpecification');
check('часы: дни ссылками на schema.org', $schema_hours[0]['dayOfWeek'][0], 'https://schema.org/Monday');

/* ---------------------------------------------------------------- разметка */

$point = array(
	'title'      => 'Вскрытие и замена замков в Приморском районе СПб',
	'url'        => 'https://example.ru/vskrytie-zamkov-primorsky/',
	'intro'      => 'Мастер приезжает за 20 минут.',
	'street'     => 'Богатырский пр., 12',
	'locality'   => 'Санкт-Петербург',
	'region'     => 'Санкт-Петербург',
	'postal'     => '197348',
	'country'    => 'RU',
	'district'   => 'Приморский район',
	'lat'        => '60.001',
	'lng'        => '30.301',
	'place_id'   => 'ChIJ_abc-123',
	'hours_spec' => $always,
	'image'      => 'https://example.ru/img/point.jpg',
);
$settings = array(
	'org_name'      => 'Мастер Замок',
	'org_url'       => 'https://example.ru/',
	'phone_e164'    => '+78121234567',
	'business_type' => 'Locksmith',
	'price_range'   => '₽₽',
	'currency'      => 'RUB',
	'same_as'       => array('https://vk.com/example'),
);
$node = Schema::location($point, $settings);

check('разметка: тип', $node['@type'], 'Locksmith');
check('разметка: идентификатор', $node['@id'], 'https://example.ru/vskrytie-zamkov-primorsky/#location');
check('разметка: телефон', $node['telephone'], '+78121234567');
check('разметка: улица', $node['address']['streetAddress'], 'Богатырский пр., 12');
check('разметка: индекс', $node['address']['postalCode'], '197348');
check('разметка: координаты числами', $node['geo']['latitude'], 60.001);
check('разметка: часы на месте', count($node['openingHoursSpecification']), 1);
check('разметка: район в areaServed', $node['areaServed'][0]['name'], 'Приморский район');
check('разметка: ссылка на карточку', $node['hasMap'], 'https://www.google.com/maps/place/?q=place_id:ChIJ_abc-123');
check('разметка: филиал организации', $node['branchOf']['name'], 'Мастер Замок');
check('разметка: sameAs с карточкой и профилем', count($node['sameAs']), 2);

// Правило, которое ломается тише всего: звёзды отзывов в разметке
// снимают расширенный вид сайта целиком.
ok('разметка: нет aggregateRating', !isset($node['aggregateRating']));
ok('разметка: нет review', !isset($node['review']) && !isset($node['reviews']));
ok('разметка: пустые поля выброшены', !array_key_exists('image', Schema::location(array('url' => 'https://a.ru/x/'), array())));

$graph = Schema::graph(array($node));
check('разметка: контекст графа', $graph['@context'], 'https://schema.org');
check('разметка: пустой граф не собирается', Schema::graph(array()), array());

$unknown_type = Schema::location($point, array_merge($settings, array('business_type' => 'Диван')));
check('разметка: неизвестный тип заменяется', $unknown_type['@type'], 'Locksmith');

/* ------------------------------------------------------------- похожесть */

$a = 'Вскрытие замков в Приморском районе Петербурга, выезд мастера за двадцать минут на Богатырский проспект';
$b = 'Вскрытие замков в Приморском районе Петербурга, выезд мастера за двадцать минут на Богатырский проспект';
$c = 'Замена личинок в Купчино у метро Международная, работаем по Будапештской и Бухарестской улицам круглосуточно';

check('похожесть: одинаковые тексты', Similarity::jaccard($a, $b), 1.0);
ok('похожесть: разные тексты', Similarity::jaccard($a, $c) < 0.1);
ok('похожесть: клон виден', Similarity::uniqueness($a, array($b)) < 0.2);
ok('похожесть: свой текст виден', Similarity::uniqueness($c, array($a)) > 0.8);
check('похожесть: пустой текст', Similarity::uniqueness('', array($a)), 0.0);
check('похожесть: регистр и знаки не считаются', Similarity::jaccard('Замок, ключ — дверь!', 'замок ключ дверь'), 1.0);

/* ----------------------------------------------------------------- таблица */

$csv = "\xEF\xBB\xBFСлаг;Заголовок;Район;Улица;Город;Метро;Часы работы\n"
	. "vskrytie-zamkov-primorsky;Приморский;Приморский район;Богатырский пр., 12;Санкт-Петербург;Комендантский проспект, Старая Деревня;круглосуточно\n"
	. ";;;;;;\n"
	. "vskrytie-zamkov-kupchino;Купчино;Фрунзенский район;Будапештская ул., 4;Санкт-Петербург;Купчино;Пн-Вс 08:00-23:00\n";
$parsed = Csv::parse($csv);

check('таблица: разделитель «;»', Csv::detect_delimiter('a;b;c'), ';');
check('таблица: разделитель «,»', Csv::detect_delimiter('a,b,c'), ',');
check('таблица: строк без пустых', count($parsed['rows']), 2);
check('таблица: ошибок нет', $parsed['errors'], array());
check('таблица: русские заголовки распознаны', $parsed['rows'][0]['slug'], 'vskrytie-zamkov-primorsky');
check('таблица: BOM не прилип к первому заголовку', $parsed['rows'][0]['district'], 'Приморский район');
check('таблица: часы прочитаны', $parsed['rows'][1]['hours'], 'Пн-Вс 08:00-23:00');
check('таблица: номер строки сохранён', $parsed['rows'][1]['_line'], 4);

$unknown = Csv::parse("slug,Комментарий\nx,привет\n");
check('таблица: неизвестный столбец назван', $unknown['unknown'], array('Комментарий'));
ok('таблица: без slug и title — ошибка', Csv::parse("Комментарий\nпривет\n")['errors'] !== array());
check('таблица: список через запятую', Csv::to_list('Купчино, Международная,  Купчино'), array('Купчино', 'Международная'));
check(
	'таблица: перенос строки внутри ячейки',
	Csv::parse("slug,content\nx,\"первая строка\nвторая строка\"\n")['rows'][0]['content'],
	"первая строка\nвторая строка"
);
check('таблица: ё и Ё не мешают', Csv::canonical_key('Населённый пункт'), 'locality');

/* ------------------------------------------------------------------ импорт */

check('импорт: слаг из URL', Import::slug_from('https://example.ru/vskrytie-zamkov-primorsky/'), 'vskrytie-zamkov-primorsky');
check('импорт: слаг из слага', Import::slug_from('vskrytie-zamkov-kupchino'), 'vskrytie-zamkov-kupchino');
check('импорт: слаг из заголовка', Import::slug_from('', 'Приморский район'), 'приморский-район');
check('импорт: пустая строка', Import::slug_from('', ''), '');

// Поле, добавленное в форму, но забытое в импорте, молча не заполнится
// на девятнадцати страницах разом.
$aliases = Csv::aliases();
foreach (array_keys(Fields::fields()) as $key) {
	ok('импорт знает поле «' . $key . '»', isset($aliases[$key]));
}

/* ------------------------------------------------------------------ отзывы */

$normalized = Reviews::normalize(array(
	'rating'          => 4.8,
	'userRatingCount' => 137,
	'googleMapsUri'   => 'https://maps.google.com/?cid=1',
	'reviews'         => array(
		array(
			'rating'                         => 5,
			'text'                           => array('text' => 'Приехали за 15 минут.'),
			'authorAttribution'              => array('displayName' => 'Иван П.'),
			'relativePublishTimeDescription' => 'месяц назад',
		),
		array('rating' => 5, 'authorAttribution' => array('displayName' => 'Без текста')),
	),
));
check('отзывы: рейтинг', $normalized['rating'], 4.8);
check('отзывы: количество', $normalized['count'], 137);
check('отзывы: пустые отзывы выброшены', count($normalized['items']), 1);
check('отзывы: автор', $normalized['items'][0]['author'], 'Иван П.');
check('отзывы: пустой ответ не ломает', Reviews::normalize(array())['items'], array());

/* ------------------------------------------------------------------ итоги */

echo "\n";
if ($failed) {
	echo "✗ Не прошло: " . count($failed) . " из " . ($passed + count($failed)) . "\n\n";
	foreach ($failed as $message) {
		echo "  " . $message . "\n\n";
	}
	exit(1);
}
echo "✓ Все проверки прошли: {$passed}\n";
exit(0);
