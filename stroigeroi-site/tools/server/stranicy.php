<?php
/*
  Серверная часть правок 25-36: страницы. Команда из сообщения заказчику
  снимает curl'ом главную, раздел, товар, контакты, «Реквизиты»,
  «Юридическим лицам», корзину, вход, «Все разделы каталога» и калькулятор
  уже после правки и базы, а этот файл их читает. Только читает; через сайт
  не работает. Страницы, которых команда не снимала, отмечаются
  «не открылась» - остальное проверяется как обычно.

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
  -- kabinet    кабинет убран (правка 28): на главной, в разделе и на товаре
                нет «Войти» и «Избранного» в шапке, колонки «Личный
                кабинет» в подвале и сердечек у товаров; на странице входа
                нет ссылок на закрытые регистрацию и восстановление пароля;
                в «Все разделы каталога» нет колонки кабинета.
  -- zagolovok  заголовок главной как его видит посетитель (правка 29:
                без «от «Строй-Героя»»).
  -- kalkulyator  страница калькулятора (правка 31): заголовок, место
                под 14 расчётов, свежий ли calc.js (v= совпадает с шаблоном
                на диске) и есть ли окно «Заказать звонок» - в него
                калькулятор прикладывает расчёт для менеджера. Сами расчёты
                рисует скрипт в браузере, в снятой curl'ом странице их нет.
  -- filtr      есть ли на странице раздела фильтр OCFilter.
  -- glavnaya   главная по концепции заказчика (правки 35-36): новый ли
                первый экран, есть ли сцена, сколько плиток разделов
                (ждём 9) и карточек магазинов (3), есть ли карта, какие
                страницы попали в синюю строку шапки («О компании»
                и «Юрлицам» - если nav-ids.php нашёл их номера, «Доставка
                и оплата» - когда появится страница).
                Второй строкой - «Популярные товары»: какие подборки
                вывел движок (заголовок и число товаров - это будущие
                вкладки), у скольких товаров вместо фото заглушка
                и сколько не-подборок (баннеров) стоит в Content Top.
                «блока нет» - в Content Top главной нет ни одной
                подборки, и калькулятор стоит во всю ширину.

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
foreach (array('glavnaya', 'razdel', 'tovar', 'kontakty', 'rekv', 'yurlicam', 'kalk') as $name) {
    $h = $page($name);
    if ($h === '') {
        echo "$name: страница не открылась\n";
        continue;
    }
    // С правки 35 телефон в шапке - header-contact__phone (раньше header-util__phone).
    $main = preg_match('/class="header-(?:contact|util)__phone" href="tel:([^"]+)"/', $h, $mm) ? $mm[1] : 'нет';
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

echo "-- kabinet\n";
foreach (array('glavnaya', 'razdel', 'tovar') as $name) {
    $h = $page($name);
    if ($h === '') {
        echo "$name: страница не открылась\n";
        continue;
    }
    $left = array();
    if (preg_match('~header-action__label">(Войти|Кабинет)<~u', $h)) {
        $left[] = '«Войти» в шапке';
    }
    if (strpos($h, 'header-action__label">Избранное<') !== false) {
        $left[] = '«Избранное» в шапке';
    }
    if (strpos($h, 'footer-group__label">Личный кабинет<') !== false) {
        $left[] = 'колонка «Личный кабинет» в подвале';
    }
    $fav = substr_count($h, 'data-add="fav"');
    if ($fav) {
        $left[] = "сердечек у товаров $fav";
    }
    echo "$name: ", $left ? 'ОСТАЛОСЬ: ' . implode(', ', $left) : 'кабинета и избранного нет', "\n";
}
$h = $page('vhod');
if ($h === '') {
    echo "вход: страница не открылась\n";
} else {
    $dead = preg_match_all('~href="[^"]*(?:account/register|account/forgotten|simpleregister|create-account|forgot-password)[^"]*"~', $h);
    echo 'вход: ', mb_strpos($h, 'Без кабинета') !== false ? 'новая страница' : 'СТАРАЯ страница',
         ', ссылок на закрытые страницы ', $dead, "\n";
}
// Только блок под каталогом: в подвале те же подписи и ссылки.
$h = $page('karta');
$from = strpos($h, 'class="sitemap-extra"');
$to = $from === false ? false : strpos($h, '<footer', $from);
if ($h === '') {
    echo "все разделы: страница не открылась\n";
} elseif ($to === false) {
    echo "все разделы: блока под каталогом нет\n";
} else {
    $x = substr($h, $from, $to - $from);
    echo 'все разделы: колонка кабинета ', strpos($x, 'footer-group__label">Личный кабинет<') !== false ? 'ЕСТЬ' : 'убрана',
         ', «Возврат товара» ', strpos($x, '>Возврат товара<') !== false ? 'есть' : 'НЕТ', "\n";
}

echo "-- glavnaya\n";
$h = $page('glavnaya');
if ($h === '') {
    echo "главная не открылась\n";
} else {
    $nav = array();
    foreach (array('О компании', 'Юрлицам', 'Доставка и оплата') as $t) {
        $nav[] = $t . (strpos($h, 'class="header-nav__link" href="') !== false
            && preg_match('~class="header-nav__link" href="[^"]+">' . preg_quote($t, '~') . '<~u', $h) ? ' есть' : ' нет');
    }
    echo 'первый экран ', strpos($h, 'class="first-screen"') !== false ? 'новый' : 'СТАРЫЙ',
         ', сцена ', strpos($h, 'image/home/scene-') !== false ? 'есть' : 'НЕТ',
         ', разделов ', substr_count($h, 'class="cat-tile"'),
         ', магазинов ', substr_count($h, 'class="store-card"'),
         // С правки 37 карта - карточка в ряду магазинов (store-card--map)
         ', карта ', strpos($h, 'store-card--map') !== false ? 'есть' : 'нет',
         ', меню: ', implode(', ', $nav), "\n";

    // Подборки: каждая начинается с <div class="selection" data-slider>.
    // Заголовок подборки - будущая вкладка; заглушка вместо фото -
    // placeholder или no_image в адресе картинки.
    $parts = explode('<div class="selection" data-slider>', $h);
    array_shift($parts);
    $sel = array();
    $cards = 0;
    $noimg = 0;
    foreach ($parts as $part) {
        $t = preg_match('~<h2 class="section__title">(.*?)</h2>~s', $part, $mm)
            ? trim(html_entity_decode(strip_tags($mm[1]), ENT_QUOTES, 'UTF-8')) : '';
        $end = strpos($part, '<div class="selection" data-slider>');
        $body = $end === false ? $part : substr($part, 0, $end);
        $n = substr_count($body, '<article class="product-card');
        $cards += $n;
        $noimg += preg_match_all('~class="product-card__photo"[^>]*><img src="[^"]*(?:placeholder|no_image)~', $body);
        $sel[] = ($t === '' ? 'без заголовка' : $t) . ' ' . $n;
    }
    $block = strpos($h, 'data-top-products') !== false;
    $rest = $block && preg_match('~data-top-products>(.*?)</section>\s*<section class="perks"~s', $h, $mm)
        ? substr_count($mm[1], 'class="promo-grid"') : 0;
    echo 'товары: ', $block ? 'блок есть' : 'блока нет',
         $sel ? ', подборки: ' . implode(', ', $sel) . ", без фото $noimg из $cards" : ', подборок нет',
         $rest ? ", баннеров в Content Top $rest (app.js уносит их под ряд)" : '',
         ', ссылок на расчёты ', substr_count($h, 'information/calculator#'), "\n";
}

echo "-- zagolovok\n";
$h = $page('glavnaya');
if ($h === '') {
    echo "главная не открылась\n";
} elseif (preg_match('~<h1 class="(?:intro|first-screen)__title"[^>]*>(.*?)</h1>~s', $h, $mm)) {
    $t = html_entity_decode(strip_tags($mm[1]), ENT_QUOTES, 'UTF-8');
    $t = trim(preg_replace('/\s+/u', ' ', str_replace("\xc2\xa0", ' ', $t)));
    echo "главная: «{$t}»\n";
} else {
    echo "главная: заголовка на месте нет\n";
}

echo "-- kalkulyator\n";
$h = $page('kalk');
if ($h === '') {
    echo "страница не открылась\n";
} else {
    $h1 = preg_match('~<h1[^>]*>(.*?)</h1>~su', $h, $mm)
        ? trim(html_entity_decode(strip_tags($mm[1]), ENT_QUOTES, 'UTF-8')) : 'нет';
    $js = preg_match('~javascript/calc\.js\?v=([0-9a-f]+)~', $h, $mm) ? $mm[1] : '';
    echo 'заголовок «', $h1, '», расчёты ', strpos($h, 'data-calcs') !== false ? 'есть' : 'НЕТ',
         ', calc.js ', $js === '' ? 'НЕТ' : ($want === '' || $js === $want ? 'ok' : "СТАРЫЙ v=$js, ждём $want"),
         ', заявка менеджеру ', strpos($h, 'id="modal-callback"') !== false ? 'есть' : 'НЕТ', "\n";
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
