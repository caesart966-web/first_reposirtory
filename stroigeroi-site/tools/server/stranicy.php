<?php
/*
  Серверная часть правки 25: страницы. Команда из сообщения заказчику
  снимает curl'ом главную, раздел, товар, контакты и «Реквизиты» уже после
  правки и базы, а этот файл их читает. Только читает; через сайт
  не работает.

  -- check      на каждой странице:
                main    номер в шапке (ждём основной, +79638319999);
                stores  сколько из трёх магазинов со своим номером (3/3);
                ph      заготовки макета (класс ph; ждём 0);
                seller  продавец в подвале - ИНН и ОГРНИП (ok);
                theme   свежая ли тема: v= у стилей на странице совпадает
                        с шаблоном на диске (ok; иначе сайт отдаёт старое
                        из кеша);
                nbsp    сколько раз на странице буквами видно «&nbsp;» (0) -
                        так было с ценами до правки 25;
                policy  ссылок у галочки согласия в «Заказать звонок»
                        (0: страница политики выключена - и ссылки нет);
                другие номера - ссылки tel: не из списка действующих.
  -- rekvizity  оформлена ли страница, кнопки «Копировать», все ли номера
                на месте, что перенесено с прежней страницы.
  -- yurlicam   «Юридическим лицам» (правка 27): карточки, цифры, кнопки
                «Копировать», и не осталось ли «N-контрагентов»,
                «крупнейших» и «филиалов».
  -- korzina    пустая корзина: «Корзина пуста», а не «404» (правка 27).
  -- filtr      есть ли на странице раздела фильтр OCFilter.

  Первая версия (правка 23) печатала ещё разметку фильтра - по ней
  фильтр и оформлен; больше она не нужна.

  Запуск: php stranicy.php <папка со снятыми страницами> <папка сайта>
*/
if (PHP_SAPI !== 'cli') {
    exit;
}
$dir = isset($argv[1]) ? rtrim($argv[1], '/') : '.';
$site = isset($argv[2]) ? rtrim($argv[2], '/') : '';

$PHONES = array('+79638319999', '+74152319999', '+79638300999', '+74152400999', '+79638300333',
                '+74152400333', '+79098904075', '+79638304111', '+79638300177', '+74152232929');
$STORES = array('+79638319999', '+79638300999', '+79638300333');
$INN = '410109423040';
$OGRN = '324410000001111';

// Версия темы на диске - та, что должна быть в ссылках на стили.
$want = '';
$tpl = $site . '/catalog/view/theme/stroigeroi2026/template/common/header.twig';
if ($site !== '' && is_file($tpl) && preg_match("/\{% set asset_v = '([^']*)' %\}/", file_get_contents($tpl), $mm)) {
    $want = $mm[1];
}

$page = function ($name) use ($dir) {
    $f = "$dir/$name.html";
    return is_file($f) ? file_get_contents($f) : '';
};

echo "-- check\n";
foreach (array('glavnaya', 'razdel', 'tovar', 'kontakty', 'rekv', 'yurlicam') as $name) {
    $h = $page($name);
    if ($h === '') {
        echo "$name: страница не открылась\n";
        continue;
    }
    $main = preg_match('/class="header-util__phone" href="tel:([^"]+)"/', $h, $mm) ? $mm[1] : 'нет';
    $stores = 0;
    foreach ($STORES as $t) {
        $stores += strpos($h, 'href="tel:' . $t . '"') !== false ? 1 : 0;
    }
    $ph = preg_match_all('/class="(?:[^"]*\s)?ph(?:\s[^"]*)?"/', $h);
    $seller = preg_match('~class="footer-brand__legal">(.*?)</p>~s', $h, $lm)
        && strpos($lm[1], "ИНН $INN") !== false && strpos($lm[1], "ОГРНИП $OGRN") !== false ? 'ok' : 'НЕТ';
    $v = preg_match('~stylesheet/opencart\.css\?v=([0-9a-f]+)~', $h, $mm) ? $mm[1] : 'нет';
    $theme = $want === '' ? "v=$v" : ($v === $want ? 'ok' : "СТАРАЯ v=$v, ждём $want");
    $nbsp = substr_count($h, '&amp;nbsp;');
    $policy = preg_match('~<label class="consent">(.*?)</label>~s', $h, $cm) ? substr_count($cm[1], '<a ') : '-';
    preg_match_all('/href="tel:([^"]+)"/', $h, $all);
    $alien = array_values(array_unique(array_diff($all[1], $PHONES)));
    echo "$name: main $main, stores $stores/3, ph $ph, seller $seller, theme $theme, nbsp $nbsp, policy $policy",
         $alien ? ', другие номера ' . implode(' ', $alien) : '', "\n";
}

echo "-- rekvizity\n";
$h = $page('rekv');
if ($h === '') {
    echo "страница не открылась\n";
} elseif (strpos($h, 'class="req"') === false) {
    echo "НЕ оформлена: на странице прежний текст\n";
} else {
    $miss = array();
    foreach (array($INN, $OGRN, '044442607', '40802810736170011017', '30101810300000000607') as $n) {
        if (strpos($h, 'data-copy="' . $n . '"') === false) {
            $miss[] = $n;
        }
    }
    echo 'оформлена: карточек ', substr_count($h, '<section class="req-card'),
         ', кнопок «Копировать» ', substr_count($h, 'data-copy="'),
         $miss ? ', НЕТ кнопок у ' . implode(' ', $miss) : ', номера все на месте',
         ', «Дополнительно» ', strpos($h, '>Дополнительно<') !== false ? 'есть' : 'нет',
         ', картинок с прежней страницы ', preg_match('~<div class="req-extra">(.*?)</div>~s', $h, $em) ? substr_count($em[1], '<img') : 0,
         "\n";
}

echo "-- yurlicam\n";
$h = $page('yurlicam');
if ($h === '') {
    echo "страница не открылась\n";
} elseif (strpos($h, 'class="b2b-features"') === false) {
    echo "НЕ оформлена: на странице прежний текст\n";
} else {
    $left = array();
    foreach (array('N-контрагент', 'крупнейш', 'филиал') as $w) {
        if (mb_strpos($h, $w) !== false) {
            $left[] = $w;
        }
    }
    echo 'оформлена: карточек ', substr_count($h, 'class="b2b-feature"'),
         ', цифр ', substr_count($h, 'class="tile"'),
         ', кнопок «Копировать» ', substr_count($h, 'data-copy="'),
         $left ? ', ОСТАЛОСЬ: ' . implode(', ', $left) : ', старых слов нет', "\n";
}

echo "-- korzina\n";
$h = $page('korzina');
if ($h === '') {
    echo "страница не открылась\n";
} else {
    echo mb_strpos($h, 'Корзина пуста') !== false ? '«Корзина пуста»' : 'нет «Корзина пуста»',
         strpos($h, 'error-page__code') !== false ? ', НО ЕСТЬ «404»' : ', без «404»', "\n";
}

echo "-- filtr\n";
$h = $page('razdel');
if ($h === '') {
    echo "страница раздела не открылась\n";
} else {
    echo 'фильтр ', strpos($h, 'id="ocfilter"') !== false ? 'есть' : 'НЕТ',
         ', мобильная обёртка ', strpos($h, 'ocfilter-mobile') !== false ? 'есть (стили темы её прячут)' : 'нет',
         "\n";
}
