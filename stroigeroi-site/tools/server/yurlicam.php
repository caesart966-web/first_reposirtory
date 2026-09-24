<?php
/*
  Серверная часть правки 27: страница «Юридическим лицам». Запускается
  из командной строки (команда в сообщении заказчику) и сразу удаляется;
  через сайт не работает.

  Текст страницы в базе заменяется оформленным - yurlicam.html рядом
  (в репозитории tools/yurlicam/yurlicam.html). На сайте 24.09.2026 там
  стоял тот же текст, что на «О компании» до правки 15: столбик голых
  строк, пустоты на месте картинок прежней темы, «один из крупнейших
  магазинов Камчатского края» (проверить нечем, а превосходная степень
  без подтверждения в рекламе запрещена - 38-ФЗ, ст. 5), «2 филиала»
  (магазинов три) и незаполненная заготовка «N-контрагентов».
  В новом тексте только то, что уже есть на сайте: цифры и слова
  заказчика с этой же страницы, три магазина, номера для юрлиц из 2ГИС,
  бухгалтерия, почта и реквизиты.

  Прежний текст переписан со снимков, поэтому сначала он сверяется
  с самой страницей: девять строк должны найтись в её тексте; не нашлась
  хоть одна - STOP, ничего не меняется. Всё, что новый текст не повторяет,
  печатается в отчёте: строки, ссылки, картинки. Прежний текст - в таблице
  legal_before; она же не даёт записать дважды. Откат - yurlicam-otkat.php.

  Запуск: php yurlicam.php <папка сайта> [файл для адреса страницы]
  Во второй файл пишется адрес страницы - по нему команда её скачивает.
*/
if (PHP_SAPI !== 'cli') {
    exit;
}
$site = isset($argv[1]) ? rtrim($argv[1], '/') : '.';
$urlFile = isset($argv[2]) ? $argv[2] : '';
require $site . '/config.php';
mysqli_report(MYSQLI_REPORT_OFF);
$m = @new mysqli(DB_HOSTNAME, DB_USERNAME, DB_PASSWORD, DB_DATABASE, (int)DB_PORT);
if ($m->connect_error) {
    echo 'DB: ', $m->connect_error, "\n";
    exit(1);
}
$m->set_charset('utf8');
$p = DB_PREFIX;
echo "-- legal\n";

$new = @file_get_contents(__DIR__ . '/yurlicam.html');
if ($new === false || strpos($new, 'class="b2b-features"') === false) {
    echo "STOP: нет файла yurlicam.html рядом - ничего не менял\n";
    exit(1);
}
$r = $m->query("SELECT information_id, language_id, description FROM `{$p}information_description` WHERE title = 'Юридическим лицам'");
if (!$r || $r->num_rows !== 1) {
    echo 'STOP: страниц с заголовком «Юридическим лицам» найдено ', $r ? $r->num_rows : '?', " - ничего не менял\n";
    exit(1);
}
$row = $r->fetch_assoc();
$id = (int)$row['information_id'];
$lang = (int)$row['language_id'];
if ($urlFile !== '') {
    file_put_contents($urlFile, 'index.php?route=information/information&information_id=' . $id);
}
$stored = $row['description'];
$escaped = strpos($stored, '&lt;') !== false;
$html = $escaped ? html_entity_decode($stored, ENT_QUOTES, 'UTF-8') : $stored;
if (strpos($html, 'class="b2b-features"') !== false) {
    echo "страница $id уже оформлена - не трогаю\n";
    exit;
}

// Текст прежней страницы строками, как их видит посетитель.
$text = preg_replace('~<(br|/p|/div|/h[1-6]|/li|/tr|/span)\b[^>]*>~i', "\n", $html);
$text = html_entity_decode(strip_tags($text), ENT_QUOTES, 'UTF-8');
$text = str_replace("\xc2\xa0", ' ', $text);
$flat = trim(preg_replace('/\s+/u', ' ', $text));

$strings = array(
    'Работаем с физическими и с юридическими лицами', 'индивидуальный подход к каждому клиенту',
    'Действует доставка', 'снабжаем объекты под ключ', 'товар в наличии, два склада отгрузки',
    'нас выбирают 150 тысяч клиентов в год', 'на рынке с 2007 года',
    'у нас более 10 тысяч товаров в наличии и под заказ', 'в нашей команде более 50 сотрудников',
);
$miss = array();
foreach ($strings as $s) {
    if (mb_strpos($flat, $s) === false) {
        $miss[] = "«{$s}»";
    }
}
if ($miss) {
    echo 'STOP: на нынешней странице не нашлось: ', implode('; ', $miss), " - ничего не менял\n";
    exit(1);
}
echo 'сверено с нынешней страницей: ', count($strings), " строк - все на месте\n";

// Что сознательно не переносится - с причиной.
$dropped = array(
    'один из крупнейших' => 'проверить нечем, превосходная степень (как на «О компании»)',
    'филиал' => 'магазинов три, а не два филиала',
    'N-контрагент' => 'незаполненная заготовка, число может дать только заказчик',
);
foreach ($dropped as $k => $why) {
    if (mb_strpos($flat, $k) !== false) {
        echo "убрано «{$k}…» - {$why}\n";
    }
}

// Строки, которых новый текст не повторяет и которых нет в списке выше.
$known = array('Строй-Герой', 'филиал', 'Работаем с физическими', 'индивидуальный подход', 'Действует доставка',
               'снабжаем объекты', 'товар в наличии', '150 000', '150 тысяч', '2007', '10 000', '10 тысяч',
               'контрагент', '50 сотрудников', 'Мы постоянно расширяем', 'Открыть реквизиты', 'Юридическим лицам');
$exact = array('N', 'товаров', '50 +', '50+');
$extra = array();
foreach (preg_split('/\n+/u', $text) as $line) {
    $line = trim(preg_replace('/\s+/u', ' ', $line));
    if ($line === '' || in_array($line, $exact, true)) {
        continue;
    }
    $covered = false;
    foreach ($known as $k) {
        if (mb_strpos($line, $k) !== false) {
            $covered = true;
            break;
        }
    }
    if (!$covered) {
        $extra[] = $line;
    }
}
foreach ($extra as $line) {
    echo 'не перенесено: «', mb_substr($line, 0, 120), "»\n";
}
preg_match_all('~<a\b[^>]*href="([^"]*)"[^>]*>(.*?)</a>~is', $html, $links, PREG_SET_ORDER);
foreach ($links as $l) {
    echo 'ссылка «', mb_substr(trim(strip_tags($l[2])), 0, 40), '» -> ', mb_substr($l[1], 0, 100), "\n";
}
preg_match_all('~<img\b[^>]*>~i', $html, $imgs);
echo 'картинок на прежней странице: ', count($imgs[0]), "\n";
foreach ($imgs[0] as $img) {
    echo '  ', preg_match('~src="([^"]*)"~i', $img, $src) ? mb_substr($src[1], 0, 100) : mb_substr($img, 0, 100), "\n";
}

if (!$m->query("CREATE TABLE `{$p}legal_before` AS SELECT * FROM `{$p}information_description` WHERE information_id = $id")) {
    echo 'STOP: ', $m->error, " - уже меняли? ничего не менял\n";
    exit(1);
}
$store = $escaped ? htmlspecialchars($new, ENT_COMPAT, 'UTF-8') : $new;
if (!$m->query("UPDATE `{$p}information_description` SET description = '" . $m->real_escape_string($store) . "' WHERE information_id = $id AND language_id = $lang")) {
    echo 'SQL: ', $m->error, "\n";
    exit(1);
}
echo "страница $id записана: ", strlen($new), ' знаков (было ', strlen($html), '), прежний текст - в ', $p, "legal_before\n";
