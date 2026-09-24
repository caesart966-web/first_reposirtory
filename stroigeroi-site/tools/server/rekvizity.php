<?php
/*
  Серверная часть правки 25: страница «Реквизиты». Запускается из
  командной строки (команда в сообщении заказчику) и сразу удаляется;
  через сайт не работает.

  Текст страницы в базе заменяется оформленным - rekvizity.html рядом
  (в репозитории tools/rekvizity/rekvizity.html). Номера и строки в нём
  переписаны со снимка нынешней страницы, поэтому сначала каждый сверяется
  с ней самой: номер ищется среди номеров нынешней страницы целиком,
  строка - в её тексте. Не нашлось хоть одно - STOP, ничего не меняется.
  Контрольные суммы ИНН, ОГРНИП и обоих счетов сошлись ещё при подготовке.
  Номера магазина на Чубарова на прежней странице не было - они взяты
  из карточки 2ГИС, как на всём сайте, и сверке не подлежат.

  Строки прежней страницы, которых новая не покрывает, и картинки
  не выбрасываются: строки встают отдельной карточкой в конце, картинки -
  под ней, и то и другое печатается в отчёте.

  Формат хранения - как у движка и как у страницы «О компании»: если
  прежний текст хранился с экранированием (&lt;p&gt;), новый тоже.
  Прежний текст - в таблице requisites_before; она же не даёт записать
  дважды. Откат - rekvizity-otkat.php.

  Запуск: php rekvizity.php <папка сайта>
*/
if (PHP_SAPI !== 'cli') {
    exit;
}
$site = isset($argv[1]) ? rtrim($argv[1], '/') : '.';
require $site . '/config.php';
mysqli_report(MYSQLI_REPORT_OFF);
$m = @new mysqli(DB_HOSTNAME, DB_USERNAME, DB_PASSWORD, DB_DATABASE, (int)DB_PORT);
if ($m->connect_error) {
    echo 'DB: ', $m->connect_error, "\n";
    exit(1);
}
$m->set_charset('utf8');
$p = DB_PREFIX;
echo "-- requisites\n";

$new = @file_get_contents(__DIR__ . '/rekvizity.html');
if ($new === false || strpos($new, 'class="req"') === false) {
    echo "STOP: нет файла rekvizity.html рядом - ничего не менял\n";
    exit(1);
}
$r = $m->query("SELECT information_id, language_id, description FROM `{$p}information_description` WHERE title = 'Реквизиты'");
if (!$r || $r->num_rows !== 1) {
    echo 'STOP: страниц с заголовком «Реквизиты» найдено ', $r ? $r->num_rows : '?', " - ничего не менял\n";
    exit(1);
}
$row = $r->fetch_assoc();
$id = (int)$row['information_id'];
$lang = (int)$row['language_id'];
$stored = $row['description'];
$escaped = strpos($stored, '&lt;') !== false;
$html = $escaped ? html_entity_decode($stored, ENT_QUOTES, 'UTF-8') : $stored;
if (strpos($html, 'class="req"') !== false) {
    echo "страница $id уже оформлена - не трогаю\n";
    exit;
}

// Текст прежней страницы: строками, как их видит посетитель.
$text = preg_replace('~<(br|/p|/div|/h[1-6]|/li|/tr)\b[^>]*>~i', "\n", $html);
$text = html_entity_decode(strip_tags($text), ENT_QUOTES, 'UTF-8');
$text = str_replace("\xc2\xa0", ' ', $text);
$flat = trim(preg_replace('/\s+/u', ' ', $text));
// Номера прежней страницы: цифры вместе с пробелами, дефисами и скобками
// между ними - «40802 810 7 3617 0011017», «8 (4152) 23-29-29».
preg_match_all('/\d[\d \-()]*\d|\d/u', $flat, $mm);
$groups = array();
foreach ($mm[0] as $g) {
    $groups[preg_replace('/\D/', '', $g)] = true;
}
$numbers = array(
    '410109423040' => 'ИНН', '324410000001111' => 'ОГРНИП', '044442607' => 'БИК',
    '40802810736170011017' => 'расчётный счёт', '30101810300000000607' => 'корр. счёт',
    '84152232929' => 'бухгалтерия', '400333' => 'Елизово, короткий', '89638300333' => 'Елизово',
    '400999' => 'Петропавловск, короткий', '89638300999' => 'Петропавловск',
);
$strings = array(
    'Лиманова Виктория Васильевна', '25.01.2024', '47.19',
    'Торговля розничная прочая в неспециализированных магазинах', 'ОСНО',
    '683002', 'ул. Ларина, 17, кв. 80', '683024', 'пр. 50 лет Октября, д. 17 А',
    'Северо-Восточное отделение №8645 ПАО Сбербанк', 'sg-pk@list.ru',
);
$miss = array();
foreach ($numbers as $n => $what) {
    if (!isset($groups[$n])) {
        $miss[] = "$what $n";
    }
}
foreach ($strings as $s) {
    if (mb_strpos($flat, $s) === false) {
        $miss[] = "«$s»";
    }
}
if ($miss) {
    echo 'STOP: на нынешней странице не нашлось: ', implode('; ', $miss), " - ничего не менял\n";
    exit(1);
}
echo 'сверено с нынешней страницей: ', count($numbers), ' номеров и ', count($strings), " строк - все на месте\n";

// Строки прежней страницы, которые новая не покрывает.
$known = array('Реквизиты', 'Индивидуальный предприниматель', 'ИНН', 'ОГРН', 'ОКВЭД', 'Юридический адрес',
               'Фактический адрес', 'Телефоны', 'Бухгалтерия', 'Магазин в г.', 'Банковские реквизиты', 'БИК',
               'Сбербанк', 'Р/СЧЕТ', 'Система', 'E-mail', 'Руководитель', '683002', '683024');
$extra = array();
foreach (preg_split('/\n+/u', $text) as $line) {
    $line = trim(preg_replace('/\s+/u', ' ', $line));
    if ($line === '') {
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
preg_match_all('~<a\b[^>]*>\s*<img\b[^>]*>\s*</a>|<img\b[^>]*>~i', $html, $imgs);
$tail = '';
if ($extra) {
    $tail .= "  <section class=\"req-card req-card--wide\">\n    <h2 class=\"req-card__title\">Дополнительно</h2>\n";
    foreach ($extra as $line) {
        $tail .= '    <p>' . htmlspecialchars($line, ENT_QUOTES, 'UTF-8') . "</p>\n";
    }
    $tail .= "  </section>\n";
}
if ($imgs[0]) {
    $tail .= "  <div class=\"req-extra\">" . implode('', $imgs[0]) . "</div>\n";
}
echo 'с прежней страницы перенесено как есть: строк ', count($extra), ', картинок ', count($imgs[0]), "\n";
foreach ($extra as $line) {
    echo '  «', mb_substr($line, 0, 100), "»\n";
}
foreach ($imgs[0] as $img) {
    echo '  ', preg_match('~src="([^"]*)"~i', $img, $src) ? mb_substr($src[1], 0, 100) : mb_substr($img, 0, 100), "\n";
}
// Перенесённое встаёт перед закрывающим </div> обёртки .req - вставкой
// по позиции, а не preg_replace: в строке замены там «$» и «\» значат своё.
$final = $new;
if ($tail !== '') {
    $at = strrpos($new, '</div>');
    $final = substr($new, 0, $at) . $tail . substr($new, $at);
}

if (!$m->query("CREATE TABLE `{$p}requisites_before` AS SELECT * FROM `{$p}information_description` WHERE information_id = $id")) {
    echo 'STOP: ', $m->error, " - уже меняли? ничего не менял\n";
    exit(1);
}
$store = $escaped ? htmlspecialchars($final, ENT_COMPAT, 'UTF-8') : $final;
if (!$m->query("UPDATE `{$p}information_description` SET description = '" . $m->real_escape_string($store) . "' WHERE information_id = $id AND language_id = $lang")) {
    echo 'SQL: ', $m->error, "\n";
    exit(1);
}
echo "страница $id записана: ", strlen($final), ' знаков (было ', strlen($html), '), прежний текст - в ', $p, "requisites_before\n";
