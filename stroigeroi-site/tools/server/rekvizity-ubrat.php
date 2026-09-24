<?php
/*
  Серверная часть правки 26: убрать со страницы «Реквизиты» блок
  «Дополнительно».

  Правка 25 не выбрасывала строки прежней страницы, которых новая
  не покрывает, а ставила их отдельной карточкой. На живом сайте ими
  оказались три надписи - «Поделиться», «Скачать», «Распечатать»:
  по всей видимости, подписи кнопок, скопированные вместе с реквизитами
  (из интернет-банка?), и ничего не делавшие. На странице они стояли
  простым текстом, заказчик попросил убрать (24.09.2026).

  Убирается карточка, только если в ней ровно эти три надписи; есть что-то
  ещё - STOP, ничего не меняется: чужой текст без спроса не удаляется.
  Заодно печатается, чем эти надписи были на прежней странице (она
  в таблице requisites_before) - ссылкой или просто текстом.

  Копии не делается: удаляются только эти три слова, а прежняя страница
  целиком уже лежит в requisites_before (откат всей правки 25 -
  rekvizity-otkat.php).

  Запуск: php rekvizity-ubrat.php <папка сайта>
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
echo "-- extra\n";

$DEAD = array('Поделиться', 'Скачать', 'Распечатать');

// Чем надписи были на прежней странице.
$r = $m->query("SELECT description FROM `{$p}requisites_before` LIMIT 1");
if ($r && ($row = $r->fetch_assoc())) {
    $old = $row['description'];
    if (strpos($old, '&lt;') !== false) {
        $old = html_entity_decode($old, ENT_QUOTES, 'UTF-8');
    }
    libxml_use_internal_errors(true);
    $d = new DOMDocument();
    $d->loadHTML('<?xml encoding="utf-8"?><div>' . $old . '</div>');
    $x = new DOMXPath($d);
    foreach ($DEAD as $word) {
        $what = 'не нашлось';
        foreach ($x->query('//text()[contains(normalize-space(.), "' . $word . '")]') as $t) {
            $what = 'просто текст, без ссылки';
            for ($el = $t->parentNode; $el && $el->nodeType === XML_ELEMENT_NODE; $el = $el->parentNode) {
                if ($el->nodeName === 'a' && trim($el->getAttribute('href')) !== '') {
                    $what = 'ссылка: ' . mb_substr($el->getAttribute('href'), 0, 120);
                    break;
                }
                if ($el->hasAttribute('onclick')) {
                    $what = 'onclick: ' . mb_substr($el->getAttribute('onclick'), 0, 120);
                    break;
                }
                if ($el->nodeName === 'button') {
                    $what = 'кнопка без ссылки';
                    break;
                }
            }
            break;
        }
        echo "на прежней странице «{$word}» - {$what}\n";
    }
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
if (strpos($html, 'class="req"') === false) {
    echo "STOP: страница $id не оформлена правкой 25 - ничего не менял\n";
    exit(1);
}
$re = '~\n?[ \t]*<section class="req-card req-card--wide">\s*<h2 class="req-card__title">Дополнительно</h2>'
    . '((?:\s*<p>[^<]*</p>)*)\s*</section>[ \t]*~u';
if (!preg_match($re, $html, $sm, PREG_OFFSET_CAPTURE)) {
    echo "блока «Дополнительно» на странице $id нет - убирать нечего\n";
    exit;
}
preg_match_all('~<p>([^<]*)</p>~u', $sm[1][0], $pm);
$lines = array();
foreach ($pm[1] as $l) {
    $lines[] = trim(html_entity_decode($l, ENT_QUOTES, 'UTF-8'));
}
$rest = array_diff($lines, $DEAD);
if ($rest || count($lines) !== count($DEAD)) {
    echo 'STOP: в блоке «Дополнительно» не только три надписи: «', implode('», «', $lines), "» - ничего не менял\n";
    exit(1);
}
$new = substr($html, 0, $sm[0][1]) . substr($html, $sm[0][1] + strlen($sm[0][0]));
if (strpos($new, 'class="req"') === false || substr_count($new, 'data-copy="') !== 5) {
    echo "STOP: после удаления страница выглядела бы не так, как ждали - ничего не менял\n";
    exit(1);
}
$store = $escaped ? htmlspecialchars($new, ENT_COMPAT, 'UTF-8') : $new;
if (!$m->query("UPDATE `{$p}information_description` SET description = '" . $m->real_escape_string($store) . "' WHERE information_id = $id AND language_id = $lang")) {
    echo 'SQL: ', $m->error, "\n";
    exit(1);
}
echo "страница $id: блок «Дополнительно» убран («", implode('», «', $lines), '»), было ', strlen($html), ' знаков, стало ', strlen($new), "\n";
