<?php
/*
  Откат stroigeroi.ru к состоянию до начала разработки (просьба заказчика
  09.10.2026: «вернуть всё до того момента, когда взяли сайт в разработку,
  и защиту от роботов тоже»).

  Всё, что мы меняли на живом сайте, меняли с копией прежнего - этот файл
  собирает все отдельные откаты в один и добавляет то, у чего отката не было
  (товары из 1С, адреса, файлы). Порядок работы - в README, раздел «Откат
  к состоянию до разработки».

    php otkat.php <папка сайта> pokaz       только показать, что найдено и что будет сделано
    php otkat.php <папка сайта> kopiya      полная копия базы и всех файлов, которые тронет откат,
                                            в ~/sg-otkat-kopiya-<дата> (вне папки сайта)
    php otkat.php <папка сайта> tema        вернуть прежнюю тему stroyhero
    php otkat.php <папка сайта> tema-nazad  снова stroigeroi2026 - если с прежней сайт не открылся
    php otkat.php <папка сайта> baza        вернуть базу
    php otkat.php <папка сайта> fajly       убрать наши файлы, вернуть .htaccess и robots.txt
    php otkat.php <папка сайта> itog        что получилось (только читает)
    php otkat.php <папка сайта> iz-kopii <папка копии>
                                            аварийно: вернуть базу и файлы из копии, то есть
                                            сайт ровно таким, каким он был перед откатом

  Что НЕ трогается: заказы и всё, что с ними связано (в них свои копии
  названий и цен), покупатели, заведённые не нами, и любые правки, которые
  делали в админке сами. Почта магазина тоже не трогается и только
  показывается: до нас там стояла почта прежнего разработчика, и вернуть
  её значило бы отправлять ему заказы.

  Печатает только числа, названия таблиц и разделов - ни имён, ни почт,
  ни телефонов покупателей. Через сайт не работает.
*/
if (PHP_SAPI !== 'cli') {
    exit;
}
$site = isset($argv[1]) ? rtrim($argv[1], '/') : '.';
$mode = isset($argv[2]) ? $argv[2] : 'pokaz';
$from = isset($argv[3]) ? rtrim($argv[3], '/') : '';
$MODES = array('pokaz', 'kopiya', 'tema', 'tema-nazad', 'baza', 'fajly', 'itog', 'iz-kopii');
if (!in_array($mode, $MODES, true)) {
    echo "STOP: режим $mode неизвестен - ", implode(', ', $MODES), "\n";
    exit(1);
}
if (!is_file($site . '/config.php') || !is_dir($site . '/catalog/view/theme')) {
    echo "STOP: в $site нет config.php или catalog/view/theme - это не папка сайта\n";
    exit(1);
}
$site = realpath($site);
require $site . '/config.php';
mysqli_report(MYSQLI_REPORT_OFF);
$m = @new mysqli(DB_HOSTNAME, DB_USERNAME, DB_PASSWORD, DB_DATABASE, (int)DB_PORT);
if ($m->connect_error) {
    echo 'DB: ', $m->connect_error, "\n";
    exit(1);
}
$m->set_charset('utf8');
// Режим самого движка (system/library/db/mysqli.php): нулевые даты в его
// таблицах записываются и читаются так же, как их пишет магазин.
$m->query("SET SESSION sql_mode = 'NO_ZERO_IN_DATE,NO_ENGINE_SUBSTITUTION'");
$p = DB_PREFIX;
$home = getenv('HOME');
if (!$home || !is_dir($home)) {
    $home = dirname(dirname($site));
}
$home = rtrim($home, '/');

// Когда началась разработка: тема залита 14.09.2026. Всё, что заведено
// раньше, - не наше, даже если попало в наши списки.
$START = '2026-09-14';
$OUR_THEME = 'stroigeroi2026';
$OLD_THEME = 'stroyhero';
$OLD_EMAIL = 'andrey@tsvetkov-design.ru';
$LK_TABLES = array('customer', 'address', 'cart', 'customer_activity', 'customer_approval', 'customer_ip',
                   'customer_online', 'customer_search', 'customer_wishlist');
// Наши служебные таблицы. После отката их быть не должно.
$OURS = array('import_1c', 'old_catalog', 'old_categories', 'hidden_categories', 'moved_categories',
              'rename_before', 'chpu_changes', 'about_before', 'requisites_before', 'legal_before',
              'phone22_before', 'phone_before', 'currency_before', 'lk_delete', 'lk_vernut');
foreach ($LK_TABLES as $t) {
    $OURS[] = 'lk_bak_' . $t;
}

$errors = 0;
$say = function ($s) {
    echo $s, "\n";
};
$q = function ($sql) use ($m, &$errors) {
    $r = $m->query($sql);
    if ($r === false) {
        echo '  SQL: ', $m->error, "\n";
        $errors++;
    }
    return $r;
};
$one = function ($sql) use ($m) {
    $r = $m->query($sql);
    $row = $r ? $r->fetch_row() : null;
    return $row ? $row[0] : null;
};
$col = function ($sql) use ($m) {
    $out = array();
    $r = $m->query($sql);
    while ($r && ($row = $r->fetch_row())) {
        $out[] = $row[0];
    }
    return $out;
};
$exists = function ($t) use ($m, $p) {
    $r = $m->query("SHOW TABLES LIKE '" . str_replace('_', '\_', $m->real_escape_string($p . $t)) . "'");
    return $r && $r->num_rows > 0;
};
$cols = function ($t) use ($m, $p) {
    $out = array();
    $r = $m->query("SHOW COLUMNS FROM `{$p}{$t}`");
    while ($r && ($row = $r->fetch_assoc())) {
        $out[] = $row['Field'];
    }
    return $out;
};
$e = function ($s) use ($m) {
    return $m->real_escape_string($s);
};
$setting = function ($key) use ($one, $e, $p) {
    return $one("SELECT `value` FROM `{$p}setting` WHERE store_id = 0 AND `key` = '" . $e($key) . "'");
};
// Таблицы базы, в которых есть колонка $name, кроме заказов, возвратов
// и наших служебных: строки заказов и возвратов хранят товар сами по себе
// и должны остаться как были.
$tablesWith = function ($name) use ($m, $p, $OURS, $e) {
    $out = array();
    $r = $m->query("SELECT TABLE_NAME FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE()"
        . " AND COLUMN_NAME = '" . $e($name) . "' ORDER BY TABLE_NAME");
    while ($r && ($row = $r->fetch_row())) {
        $t = $row[0];
        if (strpos($t, $p) !== 0) {
            continue;
        }
        $short = substr($t, strlen($p));
        if (strpos($short, 'order') === 0 || strpos($short, 'return') === 0 || in_array($short, $OURS, true)) {
            continue;
        }
        $out[] = $short;
    }
    return $out;
};
$rmTree = function ($dir) use (&$rmTree) {
    if (is_link($dir) || is_file($dir)) {
        return @unlink($dir);
    }
    if (!is_dir($dir)) {
        return true;
    }
    foreach (scandir($dir) as $f) {
        if ($f !== '.' && $f !== '..') {
            $rmTree($dir . '/' . $f);
        }
    }
    return @rmdir($dir);
};
$countFiles = function ($dir) {
    if (!is_dir($dir)) {
        return 0;
    }
    $n = 0;
    $it = new RecursiveIteratorIterator(new RecursiveDirectoryIterator($dir, FilesystemIterator::SKIP_DOTS));
    foreach ($it as $f) {
        $n++;
    }
    return $n;
};
$copyTree = function ($src, $dst) use (&$copyTree) {
    if (is_file($src)) {
        if (!is_dir(dirname($dst)) && !@mkdir(dirname($dst), 0700, true)) {
            return -1;
        }
        return @copy($src, $dst) && filesize($src) === filesize($dst) ? 1 : -1;
    }
    $n = 0;
    if (!is_dir($dst) && !@mkdir($dst, 0700, true)) {
        return -1;
    }
    foreach (scandir($src) as $f) {
        if ($f === '.' || $f === '..') {
            continue;
        }
        $k = $copyTree($src . '/' . $f, $dst . '/' . $f);
        if ($k < 0) {
            return -1;
        }
        $n += $k;
    }
    return $n;
};
$cacheDir = defined('DIR_CACHE') ? rtrim(DIR_CACHE, '/') : $site . '/system/storage/cache';
$clearCache = function () use ($cacheDir, $rmTree) {
    if (!is_dir($cacheDir)) {
        return;
    }
    foreach (scandir($cacheDir) as $f) {
        if ($f !== '.' && $f !== '..') {
            $rmTree($cacheDir . '/' . $f);
        }
    }
};

// ---- Файлы, которые трогает откат ----------------------------------------
$HT_BLOCK = "\n# stroigeroi-webp-avif: nginx passes webp/avif to Apache with no cache headers; 45 days, as nginx gives jpg/png/css/js\n"
    . "<IfModule mod_headers.c>\n  <FilesMatch \"\\.(webp|avif)$\">\n    Header set Cache-Control \"max-age=3888000\"\n  </FilesMatch>\n</IfModule>\n";
$htBak = '';
foreach (array($home . '/htaccess-2026-09-23.bak', dirname(dirname($site)) . '/htaccess-2026-09-23.bak') as $f) {
    if (is_file($f)) {
        $htBak = $f;
        break;
    }
}
$isOurRobots = function ($f) {
    $s = @file_get_contents($f);
    return $s !== false && strpos($s, 'robots.txt for the live site stroigeroi.ru') !== false;
};
$isOurController = function ($f, $class) {
    $s = @file_get_contents($f);
    return $s !== false && strpos($s, 'class ' . $class . ' extends Controller') !== false;
};
// Прежний robots.txt, если его сохраняли перед заменой (так просила
// инструкция). Не нашёлся - кладётся стоковый файл ocStore 3.0.3.7: он
// и лежал на сайте до нас, его правила записаны в нашем дословно.
$robotsSaved = function () use ($site, $home, $isOurRobots) {
    $cand = array();
    foreach (array($site, $home) as $dir) {
        foreach ((array)glob($dir . '/*robots*') as $f) {
            if (is_file($f) && $f !== $site . '/robots.txt' && filesize($f) > 0 && filesize($f) < 65536
                && !$isOurRobots($f) && stripos((string)file_get_contents($f), 'User-agent') !== false) {
                $cand[] = $f;
            }
        }
    }
    return $cand;
};
$stockRobots = __DIR__ . '/robots-ocstore-3.0.3.7.txt';
// Что лежит в корне сайта от нас: инструкция, заготовка для .htaccess,
// архивы правок и папки инструментов, если команда не успела их убрать.
$rootLeftovers = function () use ($site, $home) {
    $out = array();
    foreach (array('УСТАНОВКА.md', 'htaccess-скорость.txt', 'otkat.zip', 'sg-tools') as $f) {
        if (file_exists($site . '/' . $f)) {
            $out[] = $site . '/' . $f;
        }
    }
    foreach ((array)glob($site . '/pravka-*.zip') as $f) {
        $out[] = $f;
    }
    foreach (array('sg-lk', 'sg-tools') as $f) {
        if (file_exists($home . '/' . $f)) {
            $out[] = $home . '/' . $f;
        }
    }
    return $out;
};
$FILES = array(
    'catalog/view/theme/' . $OUR_THEME,
    'catalog/controller/information/callback.php',
    'catalog/controller/information/calculator.php',
    '.htaccess',
    'robots.txt',
);

// ---- Копия базы ----------------------------------------------------------
// Каждая инструкция кончается строкой «-- ;;», чтобы её можно было прочитать
// обратно без разбора SQL. Файл годится и для phpMyAdmin: инструкции
// обычные, с точкой с запятой.
$dump = function ($file) use ($m) {
    $gz = @gzopen($file, 'wb6');
    if (!$gz) {
        return false;
    }
    $w = function ($s) use ($gz) {
        return gzwrite($gz, $s) !== false;
    };
    // Читается в utf8mb4: в таблицах модулей может оказаться четырёхбайтный
    // символ, и через utf8 он вышел бы вопросом. Таблицам движка (utf8)
    // это ничего не меняет.
    $cs = $m->set_charset('utf8mb4') ? 'utf8mb4' : 'utf8';
    $w("-- stroigeroi.ru: копия базы перед откатом, " . date('Y-m-d H:i:s') . "\n"
        . "SET NAMES $cs;\n-- ;;\nSET FOREIGN_KEY_CHECKS = 0;\n-- ;;\nSET SESSION sql_mode = '';\n-- ;;\n");
    $tables = array();
    $r = $m->query("SHOW FULL TABLES WHERE Table_type = 'BASE TABLE'");
    while ($r && ($row = $r->fetch_row())) {
        $tables[] = $row[0];
    }
    $rows = 0;
    foreach ($tables as $t) {
        $c = $m->query("SHOW CREATE TABLE `$t`");
        $c = $c ? $c->fetch_row() : null;
        if (!$c) {
            gzclose($gz);
            return false;
        }
        $w("DROP TABLE IF EXISTS `$t`;\n-- ;;\n" . $c[1] . ";\n-- ;;\n");
        $res = $m->query("SELECT * FROM `$t`", MYSQLI_USE_RESULT);
        if (!$res) {
            gzclose($gz);
            return false;
        }
        // Двоичные строки - шестнадцатеричными литералами. Числа и даты
        // тоже приходят с кодировкой 63 («binary»), но им нужна обычная
        // запись: 0x31 в числовой колонке - это 49, а не 1.
        $bin = array();
        $BLOBS = array(MYSQLI_TYPE_TINY_BLOB, MYSQLI_TYPE_MEDIUM_BLOB, MYSQLI_TYPE_LONG_BLOB, MYSQLI_TYPE_BLOB,
                       MYSQLI_TYPE_VAR_STRING, MYSQLI_TYPE_STRING, MYSQLI_TYPE_GEOMETRY);
        foreach ($res->fetch_fields() as $i => $f) {
            $bin[$i] = ((int)$f->charsetnr === 63) && in_array((int)$f->type, $BLOBS, true);
        }
        $buf = '';
        while ($row = $res->fetch_row()) {
            $v = array();
            foreach ($row as $i => $x) {
                if ($x === null) {
                    $v[] = 'NULL';
                } elseif ($bin[$i]) {
                    $v[] = $x === '' ? "''" : '0x' . bin2hex($x);
                } else {
                    $v[] = "'" . $m->real_escape_string($x) . "'";
                }
            }
            $buf .= ($buf === '' ? "INSERT INTO `$t` VALUES\n(" : ",\n(") . implode(',', $v) . ')';
            $rows++;
            if (strlen($buf) > 200000) {
                $w($buf . ";\n-- ;;\n");
                $buf = '';
            }
        }
        $res->free();
        if ($buf !== '') {
            $w($buf . ";\n-- ;;\n");
        }
    }
    $w("SET FOREIGN_KEY_CHECKS = 1;\n-- ;;\n-- dump complete: " . count($tables) . " tables, $rows rows\n");
    gzclose($gz);
    return array(count($tables), $rows);
};
$dumpComplete = function ($file) {
    $gz = @gzopen($file, 'rb');
    if (!$gz) {
        return false;
    }
    $last = '';
    $drops = 0;
    while (($line = gzgets($gz, 1 << 20)) !== false) {
        if (strpos($line, 'DROP TABLE IF EXISTS `') === 0) {
            $drops++;
        }
        if (trim($line) !== '') {
            $last = $line;
        }
    }
    gzclose($gz);
    return preg_match('/^-- dump complete: (\d+) tables/', $last, $mm) && (int)$mm[1] === $drops ? $drops : false;
};

// ==========================================================================
//  Блоки базы. Каждый в режиме показа только считает, в режиме baza делает.
// ==========================================================================
$blocks = array();

// 1. Адреса: 18 адресов разделов, записанных нами, и три адреса-обхода
//    закрытой регистрации, которые мы убрали (create-account, forgot-password).
//    Возврат обхода - это и есть «защиту от роботов тоже вернуть».
$blocks['adresa'] = function ($do) use ($exists, $one, $col, $q, $p, $say, $setting) {
    if (!$exists('chpu_changes')) {
        $say('адреса: нашей таблицы chpu_changes нет - адреса не трогали или уже вернули');
    } else {
        $added = (int)$one("SELECT COUNT(*) FROM `{$p}chpu_changes` WHERE action = 'added'");
        $gone = $col("SELECT keyword FROM `{$p}chpu_changes` WHERE action = 'removed'");
        $live = (int)$one("SELECT COUNT(*) FROM `{$p}seo_url` s JOIN `{$p}chpu_changes` c ON c.action = 'added'"
            . " AND s.store_id = c.store_id AND s.language_id = c.language_id AND s.query = c.query AND s.keyword = c.keyword");
        $say("адреса: добавлено нами $added (на месте $live) - уберу; убрано нами " . count($gone)
            . ' (' . implode(', ', $gone) . ') - верну');
        if ($do) {
            $ok = $q("DELETE s FROM `{$p}seo_url` s JOIN `{$p}chpu_changes` c ON c.action = 'added'"
                . " AND s.store_id = c.store_id AND s.language_id = c.language_id AND s.query = c.query AND s.keyword = c.keyword")
                && $q("INSERT IGNORE INTO `{$p}seo_url` (seo_url_id, store_id, language_id, query, keyword)"
                    . " SELECT seo_url_id, store_id, language_id, query, keyword FROM `{$p}chpu_changes` WHERE action = 'removed'");
            $left = (int)$one("SELECT COUNT(*) FROM `{$p}seo_url` s JOIN `{$p}chpu_changes` c ON c.action = 'added'"
                . " AND s.store_id = c.store_id AND s.language_id = c.language_id AND s.query = c.query AND s.keyword = c.keyword");
            $back = (int)$one("SELECT COUNT(*) FROM `{$p}seo_url` s JOIN `{$p}chpu_changes` c ON c.action = 'removed'"
                . " AND s.seo_url_id = c.seo_url_id AND s.keyword = c.keyword");
            if ($ok && $left === 0 && $back === count($gone)) {
                $q("DROP TABLE `{$p}chpu_changes`");
                $say("  сделано: убрано $live, возвращено $back");
            } else {
                $say("  НЕ ВЫШЛО: осталось наших $left, вернулось $back из " . count($gone) . ' - таблицу chpu_changes оставил');
            }
        }
    }
    // ЧПУ до нас были выключены (config_seo_url = 0), включили 23.09.
    $seo = $setting('config_seo_url');
    $say('ЧПУ: ' . ($seo === '1' ? 'включены - выключу, как было до нас' : 'выключены, как до нас'));
    if ($do && $seo === '1') {
        $q("UPDATE `{$p}setting` SET `value` = '0' WHERE store_id = 0 AND `key` = 'config_seo_url'");
        $say('  сделано: config_seo_url = ' . $setting('config_seo_url'));
    }
};

// 2. Каталог из 1С: 239 товаров и 14 разделов, заведённые import.sql,
//    состояние склада «Уточняйте наличие», перенос и переименование
//    разделов из 1С. Удаляется то же, что удаляет сама админка
//    (admin/model/catalog/product.php и category.php), плюс строки
//    любых модулей с номером этого товара или раздела, кроме заказов
//    и возвратов.
$blocks['katalog1c'] = function ($do) use ($exists, $one, $col, $q, $p, $say, $tablesWith, $START, $e, $m) {
    $older = 0;
    if ($exists('import_1c')) {
        $prods = $col("SELECT DISTINCT p.product_id FROM `{$p}import_1c` i JOIN `{$p}product` p ON p.product_id = i.product_id"
            . " WHERE p.date_added >= '$START'");
        $older = (int)$one("SELECT COUNT(DISTINCT p.product_id) FROM `{$p}import_1c` i JOIN `{$p}product` p ON p.product_id = i.product_id"
            . " WHERE p.date_added < '$START'");
        $cats = $col("SELECT DISTINCT c.category_id FROM `{$p}import_1c` i JOIN `{$p}category` c ON c.category_id = i.category_id"
            . " WHERE c.date_added >= '$START'");
        $how = 'по таблице import_1c';
    } else {
        // Промежуточную таблицу могли удалить. Товар из 1С узнаётся и без
        // неё: в SKU лежит номер из 1С (GUID), заведён после начала
        // разработки. Разделы из 1С - те, что переносили внутрь отделов.
        $prods = $col("SELECT product_id FROM `{$p}product` WHERE date_added >= '$START'"
            . " AND sku REGEXP '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'");
        $cats = $exists('moved_categories') ? $col("SELECT DISTINCT c.category_id FROM `{$p}moved_categories` mc"
            . " JOIN `{$p}category` c ON c.category_id = mc.category_id WHERE c.date_added >= '$START'") : array();
        $how = 'без таблицы import_1c - по номерам 1С в SKU';
    }
    if (!$prods && !$cats) {
        $say('1С: товаров и разделов из 1С нет - не заводили или уже убрали');
    } else {
        // Подразделы, которые кто-то завёл внутри разделов из 1С: тогда
        // раздел не удаляется, а называется в отчёте.
        $kids = $cats ? $col("SELECT DISTINCT cp.category_id FROM `{$p}category_path` cp WHERE cp.path_id IN ("
            . implode(',', array_map('intval', $cats)) . ') AND cp.category_id NOT IN (' . implode(',', array_map('intval', $cats)) . ')') : array();
        if ($kids) {
            $say('1С: внутри разделов из 1С есть чужие подразделы (' . count($kids) . ') - разделы из 1С не удаляю');
            $cats = array();
        }
        $inOrders = $prods ? (int)$one("SELECT COUNT(*) FROM `{$p}order_product` WHERE product_id IN (" . implode(',', array_map('intval', $prods)) . ')') : 0;
        $foreign = $cats ? (int)$one("SELECT COUNT(DISTINCT product_id) FROM `{$p}product_to_category` WHERE category_id IN ("
            . implode(',', array_map('intval', $cats)) . ')' . ($prods ? ' AND product_id NOT IN (' . implode(',', array_map('intval', $prods)) . ')' : '')) : 0;
        $say('1С (' . $how . '): товаров ' . count($prods) . ', разделов ' . count($cats) . ' - удалю'
            . ($older ? "; ещё $older товаров из списка заведены до разработки - их не трогаю" : '')
            . ($foreign ? "; в разделах из 1С ещё $foreign чужих товаров - сами товары останутся" : '')
            . ($inOrders ? "; в заказах строк с этими товарами $inOrders - заказы не трогаю, в них свои названия и цены" : ''));
    }
    $ids = implode(',', array_map('intval', $prods));
    $cids = implode(',', array_map('intval', $cats));
    $ptables = $tablesWith('product_id');
    $ctables = $tablesWith('category_id');
    if ($prods) {
        $parts = array();
        foreach ($ptables as $t) {
            $n = (int)$one("SELECT COUNT(*) FROM `{$p}{$t}` WHERE product_id IN ($ids)");
            if ($t === 'product_related') {
                $n += (int)$one("SELECT COUNT(*) FROM `{$p}{$t}` WHERE related_id IN ($ids) AND product_id NOT IN ($ids)");
            }
            if ($n) {
                $parts[] = "$t $n";
            }
        }
        $n = (int)$one("SELECT COUNT(*) FROM `{$p}seo_url` WHERE query IN ('product_id=" . implode("','product_id=", array_map('intval', $prods)) . "')");
        $parts[] = "seo_url $n";
        $say('  строки товаров: ' . implode(', ', $parts));
    }
    if ($cats) {
        $parts = array();
        foreach ($ctables as $t) {
            $n = (int)$one("SELECT COUNT(*) FROM `{$p}{$t}` WHERE category_id IN ($cids)");
            if ($t === 'category_path') {
                $n += (int)$one("SELECT COUNT(*) FROM `{$p}{$t}` WHERE path_id IN ($cids) AND category_id NOT IN ($cids)");
            }
            if ($n) {
                $parts[] = "$t $n";
            }
        }
        $n = (int)$one("SELECT COUNT(*) FROM `{$p}seo_url` WHERE query IN ('category_id=" . implode("','category_id=", array_map('intval', $cats)) . "')");
        $parts[] = "seo_url $n";
        $say('  строки разделов: ' . implode(', ', $parts));
    }
    // Состояние склада, которое завела загрузка.
    $stock = $col("SELECT stock_status_id FROM `{$p}stock_status` WHERE name = 'Уточняйте наличие'");
    if ($stock) {
        $used = (int)$one("SELECT COUNT(*) FROM `{$p}product` WHERE stock_status_id IN (" . implode(',', array_map('intval', $stock)) . ')'
            . ($prods ? " AND product_id NOT IN ($ids)" : ''));
        $say('  состояние склада «Уточняйте наличие»: ' . ($used ? "у других товаров $used - оставлю" : 'удалю'));
    }
    $moved = $exists('moved_categories') ? (int)$one("SELECT COUNT(*) FROM `{$p}moved_categories`") : -1;
    $renamed = $exists('rename_before') ? (int)$one("SELECT COUNT(*) FROM `{$p}rename_before`") : -1;
    if ($moved >= 0 || $renamed >= 0) {
        $say('  перенос разделов из 1С: ' . ($moved >= 0 ? "$moved" : 'нет таблицы') . '; переименование: ' . ($renamed >= 0 ? "$renamed" : 'нет таблицы'));
    }
    if (!$do || (!$prods && !$cats && !$stock && $moved < 0 && $renamed < 0)) {
        return;
    }
    if ($prods) {
        foreach ($ptables as $t) {
            $q("DELETE FROM `{$p}{$t}` WHERE product_id IN ($ids)");
        }
        if (in_array('product_related', $ptables, true)) {
            $q("DELETE FROM `{$p}product_related` WHERE related_id IN ($ids)");
        }
        $q("DELETE FROM `{$p}seo_url` WHERE query IN ('product_id=" . implode("','product_id=", array_map('intval', $prods)) . "')");
    }
    if ($cats) {
        foreach ($ctables as $t) {
            $q("DELETE FROM `{$p}{$t}` WHERE category_id IN ($cids)");
        }
        if (in_array('category_path', $ctables, true)) {
            $q("DELETE FROM `{$p}category_path` WHERE path_id IN ($cids)");
        }
        $q("DELETE FROM `{$p}seo_url` WHERE query IN ('category_id=" . implode("','category_id=", array_map('intval', $cats)) . "')");
    }
    if ($stock) {
        $q("DELETE FROM `{$p}stock_status` WHERE name = 'Уточняйте наличие' AND stock_status_id NOT IN"
            . " (SELECT stock_status_id FROM (SELECT DISTINCT stock_status_id FROM `{$p}product`) x)");
    }
    // Разделы, которые переносили и которые остались (не из этой загрузки),
    // встают на прежнее место; путь пересобирается, как это делает админка.
    if ($moved >= 0) {
        $r = $m->query("SELECT mc.category_id, mc.old_parent, mc.old_top FROM `{$p}moved_categories` mc"
            . " JOIN `{$p}category` c ON c.category_id = mc.category_id WHERE mc.old_parent IS NOT NULL");
        $back = 0;
        while ($r && ($row = $r->fetch_assoc())) {
            $q("UPDATE `{$p}category` SET parent_id = " . (int)$row['old_parent'] . ', top = ' . (int)$row['old_top']
                . ' WHERE category_id = ' . (int)$row['category_id']);
            $back++;
        }
        if ($back) {
            $repair = function ($parent) use (&$repair, $m, $q, $p) {
                $r = $m->query("SELECT category_id FROM `{$p}category` WHERE parent_id = " . (int)$parent);
                $kids = array();
                while ($r && ($row = $r->fetch_row())) {
                    $kids[] = (int)$row[0];
                }
                foreach ($kids as $id) {
                    $q("DELETE FROM `{$p}category_path` WHERE category_id = $id");
                    $level = 0;
                    $pr = $m->query("SELECT path_id FROM `{$p}category_path` WHERE category_id = " . (int)$parent . ' ORDER BY level ASC');
                    while ($pr && ($x = $pr->fetch_row())) {
                        $q("INSERT INTO `{$p}category_path` SET category_id = $id, path_id = " . (int)$x[0] . ", level = $level");
                        $level++;
                    }
                    $q("REPLACE INTO `{$p}category_path` SET category_id = $id, path_id = $id, level = $level");
                    $repair($id);
                }
            };
            $repair(0);
        }
        $q("DROP TABLE `{$p}moved_categories`");
    }
    if ($renamed >= 0) {
        $q("UPDATE `{$p}category_description` d JOIN `{$p}rename_before` b ON b.category_id = d.category_id"
            . ' AND b.language_id = d.language_id SET d.name = b.name, d.meta_title = b.meta_title');
        $q("DROP TABLE `{$p}rename_before`");
    }
    $leftP = $prods ? (int)$one("SELECT COUNT(*) FROM `{$p}product` WHERE product_id IN ($ids)") : 0;
    $leftC = $cats ? (int)$one("SELECT COUNT(*) FROM `{$p}category` WHERE category_id IN ($cids)") : 0;
    if ($exists('import_1c') && $leftP === 0 && $leftC === 0) {
        $q("DROP TABLE `{$p}import_1c`");
    }
    $say('  сделано: товаров из 1С осталось ' . $leftP . ', разделов ' . $leftC);
};

// 3. Прежний каталог (180 товаров) и разделы: статусы до разработки.
//    old_catalog и old_categories - список и прежнее состояние, записанные
//    перед тем, как прятать; hidden_categories - 12 скрытых как мусор.
//    Возвращается каждая колонка old_<имя>, у которой в таблице движка
//    есть колонка <имя> (так записано «прежнее состояние»).
$restoreOld = function ($table, $target, $key, $do) use ($exists, $cols, $one, $q, $p, $say) {
    if (!$exists($table)) {
        $say("$table: нет - нечего возвращать");
        return;
    }
    $have = $cols($table);
    $base = $cols($target);
    $pairs = array();
    foreach ($have as $c) {
        if (strpos($c, 'old_') === 0 && in_array(substr($c, 4), $base, true)) {
            $pairs[substr($c, 4)] = $c;
        } elseif ($c === 'status' && in_array('status', $base, true) && !isset($pairs['status'])) {
            $pairs['status'] = 'status';
        }
    }
    if (!in_array($key, $have, true) || !$pairs) {
        $say("$table: STOP - не знаю, как прочитать (колонки: " . implode(', ', $have) . ') - не трогаю');
        return;
    }
    $n = (int)$one("SELECT COUNT(*) FROM `{$p}{$table}`");
    $cond = array();
    foreach ($pairs as $c => $old) {
        $cond[] = "NOT (t.`$c` <=> o.`$old`)";
    }
    $diff = (int)$one("SELECT COUNT(*) FROM `{$p}{$target}` t JOIN `{$p}{$table}` o ON o.`$key` = t.`$key` WHERE " . implode(' OR ', $cond));
    $say("$table: строк $n, отличается от прежнего $diff (" . implode(', ', array_keys($pairs)) . ') - верну');
    if (!$do) {
        return;
    }
    $set = array();
    foreach ($pairs as $c => $old) {
        $set[] = "t.`$c` = o.`$old`";
    }
    $q("UPDATE `{$p}{$target}` t JOIN `{$p}{$table}` o ON o.`$key` = t.`$key` SET " . implode(', ', $set));
    $left = (int)$one("SELECT COUNT(*) FROM `{$p}{$target}` t JOIN `{$p}{$table}` o ON o.`$key` = t.`$key` WHERE " . implode(' OR ', $cond));
    if ($left === 0) {
        $q("DROP TABLE `{$p}{$table}`");
        $say("  сделано");
    } else {
        $say("  НЕ ВЫШЛО: отличается $left - таблицу $table оставил");
    }
};
$blocks['prezhnie'] = function ($do) use ($restoreOld) {
    $restoreOld('old_catalog', 'product', 'product_id', $do);
    $restoreOld('hidden_categories', 'category', 'category_id', $do);
    $restoreOld('old_categories', 'category', 'category_id', $do);
};

// 4. Слайдер прежней темы carousel.29 «Основной слайдер»: выключили
//    в админке 23.09. Включается тем же способом, что админка: настройки
//    модуля - json_encode, меняется только status.
$blocks['slajder'] = function ($do) use ($m, $one, $q, $p, $say, $e) {
    $row = $m->query("SELECT module_id, name, setting FROM `{$p}module` WHERE module_id = 29 AND code = 'carousel'");
    $row = $row ? $row->fetch_assoc() : null;
    if (!$row) {
        $say('слайдер carousel.29: нет в базе - нечего включать');
        return;
    }
    $set = json_decode($row['setting'], true);
    if (!is_array($set)) {
        $say('слайдер carousel.29: STOP - настройки не читаются, не трогаю');
        return;
    }
    if (!empty($set['status'])) {
        $say('слайдер carousel.29 «' . $row['name'] . '»: включён, как до нас');
        return;
    }
    $say('слайдер carousel.29 «' . $row['name'] . '»: выключен - включу');
    if ($do) {
        $set['status'] = '1';
        $q("UPDATE `{$p}module` SET setting = '" . $e(json_encode($set)) . "' WHERE module_id = 29");
        $now = json_decode((string)$one("SELECT setting FROM `{$p}module` WHERE module_id = 29"), true);
        $say('  сделано: ' . (!empty($now['status']) ? 'включён' : 'НЕ ВЫШЛО'));
    }
};

// 5. Тексты страниц «О компании», «Реквизиты», «Юридическим лицам».
$blocks['stranicy'] = function ($do) use ($exists, $one, $q, $p, $say) {
    foreach (array('about_before' => '«О компании»', 'requisites_before' => '«Реквизиты»', 'legal_before' => '«Юридическим лицам»') as $t => $name) {
        if (!$exists($t)) {
            $say("страница $name: копии $t нет - текст не меняли или уже вернули");
            continue;
        }
        $n = (int)$one("SELECT COUNT(*) FROM `{$p}$t`");
        $diff = (int)$one("SELECT COUNT(*) FROM `{$p}information_description` d JOIN `{$p}$t` b ON b.information_id = d.information_id"
            . " AND b.language_id = d.language_id WHERE NOT (d.description <=> b.description)");
        $say("страница $name: в копии $n, отличается $diff - верну прежний текст");
        if ($do) {
            $q("UPDATE `{$p}information_description` d JOIN `{$p}$t` b ON b.information_id = d.information_id"
                . ' AND b.language_id = d.language_id SET d.description = b.description');
            $left = (int)$one("SELECT COUNT(*) FROM `{$p}information_description` d JOIN `{$p}$t` b ON b.information_id = d.information_id"
                . " AND b.language_id = d.language_id WHERE NOT (d.description <=> b.description)");
            if ($left === 0) {
                $q("DROP TABLE `{$p}$t`");
                $say('  сделано');
            } else {
                $say("  НЕ ВЫШЛО: отличается $left - копию $t оставил");
            }
        }
    }
};

// 6. Телефон магазина в настройках (правки 21-22) и знак рубля (правка 25).
$blocks['telefon'] = function ($do) use ($exists, $m, $one, $q, $p, $say, $e) {
    foreach (array('phone22_before', 'phone_before') as $t) {
        if (!$exists($t)) {
            continue;
        }
        $rows = array();
        $r = $m->query("SELECT tbl, where_sql, col, old_value FROM `{$p}$t`");
        while ($r && ($row = $r->fetch_assoc())) {
            $rows[] = $row;
        }
        $say("телефон в настройках ($t): значений " . count($rows) . ' - верну прежние');
        if ($do) {
            $bad = 0;
            foreach ($rows as $row) {
                if (!$q('UPDATE `' . $row['tbl'] . '` SET `' . $row['col'] . "` = '" . $e($row['old_value']) . "' WHERE " . $row['where_sql'])) {
                    $bad++;
                }
            }
            if (!$bad) {
                $q("DROP TABLE `{$p}$t`");
            }
            $say('  сделано' . ($bad ? ", не вышло $bad - копию $t оставил" : ''));
        }
        $found = true;
    }
    if (empty($found)) {
        $say('телефон в настройках: копий phone22_before и phone_before нет - не меняли или уже вернули');
    }
    if (!$exists('currency_before')) {
        $say('знак рубля: копии currency_before нет - не меняли или уже вернули');
    } else {
        $say('знак рубля: верну прежний из currency_before');
        if ($do) {
            $q("UPDATE `{$p}currency` c JOIN `{$p}currency_before` b ON b.currency_id = c.currency_id SET c.symbol_right = b.symbol_right");
            $left = (int)$one("SELECT COUNT(*) FROM `{$p}currency` c JOIN `{$p}currency_before` b ON b.currency_id = c.currency_id"
                . ' WHERE NOT (c.symbol_right <=> b.symbol_right)');
            if ($left === 0) {
                $q("DROP TABLE `{$p}currency_before`");
            }
            $say('  сделано' . ($left ? ' не до конца - копию оставил' : ''));
        }
    }
};

// 7. Кабинеты, удалённые 24.09 (lk-chistka.php), - обратно из lk_bak_*,
//    по правилам lk-chistka-otkat.php: номер, занятый новым кабинетом,
//    не возвращается (свой узнаётся по почте и дате заведения).
$blocks['kabinety'] = function ($do) use ($exists, $one, $q, $p, $say, $m, $LK_TABLES) {
    if (!$exists('lk_bak_customer')) {
        $say('кабинеты: копии lk_bak_customer нет - не удаляли или уже вернули');
        return;
    }
    $n = (int)$one("SELECT COUNT(*) FROM `{$p}lk_bak_customer`");
    $taken = (int)$one("SELECT COUNT(*) FROM `{$p}lk_bak_customer` b JOIN `{$p}customer` c ON c.customer_id = b.customer_id"
        . ' WHERE NOT (c.email = b.email AND c.date_added = b.date_added)');
    $here = (int)$one("SELECT COUNT(*) FROM `{$p}lk_bak_customer` b JOIN `{$p}customer` c ON c.customer_id = b.customer_id"
        . ' AND c.email = b.email AND c.date_added = b.date_added');
    $say("кабинеты: удалено нами $n, уже на месте $here, номер занят другим $taken - верну " . ($n - $here - $taken)
        . '; сейчас кабинетов ' . $one("SELECT COUNT(*) FROM `{$p}customer`"));
    if (!$do) {
        return;
    }
    $q("DROP TABLE IF EXISTS `{$p}lk_vernut`");
    if (!$q("CREATE TABLE `{$p}lk_vernut` (customer_id INT NOT NULL PRIMARY KEY)")
        || !$q("INSERT INTO `{$p}lk_vernut` SELECT b.customer_id FROM `{$p}lk_bak_customer` b"
            . " LEFT JOIN `{$p}customer` c ON c.customer_id = b.customer_id"
            . ' WHERE c.customer_id IS NULL OR (c.email = b.email AND c.date_added = b.date_added)')) {
        $say('  НЕ ВЫШЛО - кабинеты не трогал');
        return;
    }
    $lost = 0;
    $parts = array();
    foreach ($LK_TABLES as $t) {
        if (!$exists('lk_bak_' . $t)) {
            continue;
        }
        if (!$q("INSERT IGNORE INTO `{$p}{$t}` SELECT b.* FROM `{$p}lk_bak_{$t}` b JOIN `{$p}lk_vernut` r ON r.customer_id = b.customer_id")) {
            $lost++;
            continue;
        }
        $parts[] = $t . ' ' . $m->affected_rows;
        $keys = array();
        $r = $m->query("SHOW KEYS FROM `{$p}{$t}` WHERE Key_name = 'PRIMARY'");
        while ($r && ($x = $r->fetch_assoc())) {
            $keys[] = $x['Column_name'];
        }
        if (!$keys) {
            $lost++;
            continue;
        }
        $on = array();
        foreach ($keys as $c) {
            $on[] = "x.`$c` = b.`$c`";
        }
        $miss = (int)$one("SELECT COUNT(*) FROM `{$p}lk_bak_{$t}` b JOIN `{$p}lk_vernut` r ON r.customer_id = b.customer_id"
            . " LEFT JOIN `{$p}{$t}` x ON " . implode(' AND ', $on) . " WHERE x.`{$keys[0]}` IS NULL");
        $lost += $miss === 0 ? 0 : 1;
    }
    $say('  возвращено строк: ' . implode(', ', $parts) . '; кабинетов теперь ' . $one("SELECT COUNT(*) FROM `{$p}customer`"));
    if ($taken === 0 && $lost === 0) {
        foreach ($LK_TABLES as $t) {
            if ($exists('lk_bak_' . $t)) {
                $q("DROP TABLE `{$p}lk_bak_{$t}`");
            }
        }
        $q("DROP TABLE IF EXISTS `{$p}lk_delete`");
        $q("DROP TABLE IF EXISTS `{$p}lk_vernut`");
        $say('  сделано: вернулось всё, копии lk_bak_* удалены');
    } else {
        $say("  вернулось не всё: номер занят - $taken, таблиц с пропусками - $lost; копии lk_bak_* оставил");
    }
};

// 8. Шаблоны нашей темы, сохранённые через редактор шаблонов админки.
$blocks['redaktor'] = function ($do) use ($one, $q, $p, $say, $OUR_THEME, $exists) {
    if (!$exists('theme')) {
        return;
    }
    $n = (int)$one("SELECT COUNT(*) FROM `{$p}theme` WHERE theme = '$OUR_THEME'");
    if ($n) {
        $say("редактор шаблонов: записей для $OUR_THEME $n - удалю");
        if ($do) {
            $q("DELETE FROM `{$p}theme` WHERE theme = '$OUR_THEME'");
        }
    }
};

// Порядок: кабинеты раньше каталога из 1С - корзины и избранное, которые
// вернутся вместе с кабинетами, должны потерять товары из 1С вместе со всем
// остальным.
$ORDER = array('adresa', 'kabinety', 'katalog1c', 'prezhnie', 'slajder', 'stranicy', 'telefon', 'redaktor');

// Настройки, которые меняли руками по нашим инструкциям, если меняли.
// Прежнее значение известно не у всех, поэтому здесь только показ.
$showSettings = function () use ($setting, $say, $OLD_EMAIL, $one, $p) {
    $mail = (string)$setting('config_email');
    $say('почта магазина: ' . ($mail === $OLD_EMAIL ? 'та же, что до нас (прежнего разработчика)'
        : 'не та, что до нас - НЕ трогаю: на прежнюю почту уходили бы заказы прежнему разработчику'));
    $cap = (string)$setting('config_captcha');
    $pages = json_decode((string)$setting('config_captcha_page'), true);
    $say('капча: ' . ($cap === '' ? 'выключена' : "$cap, страницы: " . (is_array($pages) && $pages ? implode(', ', $pages) : 'нет')));
    $v = function ($key) use ($setting) {
        $x = $setting($key);
        return $x === null ? 'нет настройки' : ($x === '' ? 'пусто' : $x);
    };
    $say('оформление при отсутствии товара: ' . $v('config_stock_checkout') . ', предупреждение об отсутствии: '
        . $v('config_stock_warning') . ', показ остатка: ' . $v('config_stock_display'));
    $say('картинки в списке товаров: ' . $setting('theme_default_image_product_width') . 'x' . $setting('theme_default_image_product_height')
        . ' (до нас было 300x300)');
    $say('лента Sitemap: ' . $v('feed_google_sitemap_status')
        . ', модулей в макете главной: ' . $one("SELECT COUNT(*) FROM `{$p}layout_module` lm JOIN `{$p}layout_route` lr"
            . " ON lr.layout_id = lm.layout_id AND lr.route = 'common/home' AND lr.store_id = 0"));
};

// ==========================================================================
//  Файлы
// ==========================================================================
$filesPlan = function ($do) use ($site, $home, $say, $OUR_THEME, $setting, $isOurController, $isOurRobots, $robotsSaved,
                                 $stockRobots, $rootLeftovers, $rmTree, $countFiles, $HT_BLOCK, $htBak) {
    $themeDir = $site . '/catalog/view/theme/' . $OUR_THEME;
    $active = $setting('theme_default_directory');
    if (is_dir($themeDir)) {
        $say("папка темы $OUR_THEME: файлов " . $countFiles($themeDir) . ($active !== $OUR_THEME ? ' - удалю'
            : ($do ? ' - тема ещё включена, папку НЕ удаляю' : ' - удалю, когда вернётся прежняя тема')));
        if ($do && $active !== $OUR_THEME) {
            $rmTree($themeDir);
            $say('  сделано: ' . (is_dir($themeDir) ? 'НЕ ВЫШЛО, папка на месте' : 'папки нет'));
        }
    } else {
        $say("папка темы $OUR_THEME: нет");
    }
    foreach (array('callback.php' => 'ControllerInformationCallback', 'calculator.php' => 'ControllerInformationCalculator') as $f => $class) {
        $path = $site . '/catalog/controller/information/' . $f;
        if (!is_file($path)) {
            $say("контроллер $f: нет");
        } elseif (!$isOurController($path, $class)) {
            $say("контроллер $f: не наш (нет класса $class) - не трогаю");
        } else {
            $say("контроллер $f: наш - удалю");
            if ($do) {
                @unlink($path);
                $say('  сделано: ' . (is_file($path) ? 'НЕ ВЫШЛО' : 'файла нет'));
            }
        }
    }
    // .htaccess: наш блок - ровно те строки, что дописала команда 23.09.
    $ht = $site . '/.htaccess';
    $s = is_file($ht) ? file_get_contents($ht) : false;
    if ($s === false) {
        $say('.htaccess: нет файла');
    } elseif (strpos($s, 'stroigeroi-webp-avif') === false) {
        $say('.htaccess: нашего блока нет');
    } else {
        $pos = strpos($s, $HT_BLOCK);
        $clean = $pos === false ? false : substr($s, 0, $pos) . substr($s, $pos + strlen($HT_BLOCK));
        $same = ($clean !== false && $htBak !== '' && $clean === file_get_contents($htBak));
        if ($clean === false) {
            $say('.htaccess: наш блок изменён руками - STOP, не трогаю');
        } else {
            $say('.htaccess: наш блок есть - сниму; копия 23.09 ' . ($htBak === '' ? 'не найдена'
                : ($same ? 'совпадёт с результатом байт в байт' : 'НЕ совпадёт: файл после 23.09 меняли ещё - их правки оставлю')));
            if ($do) {
                $ok = file_put_contents($ht, $clean) === strlen($clean);
                $say('  сделано: ' . ($ok ? 'блока нет' : 'НЕ ВЫШЛО'));
                if ($ok && $same) {
                    @unlink($htBak);
                }
            }
        }
    }
    $rb = $site . '/robots.txt';
    if (!is_file($rb)) {
        $say('robots.txt: нет файла');
    } elseif (!$isOurRobots($rb)) {
        $say('robots.txt: не наш - не трогаю');
    } else {
        $saved = $robotsSaved();
        if (count($saved) === 1) {
            $say('robots.txt: наш - верну сохранённый прежний (' . basename($saved[0]) . ')');
            $src = $saved[0];
        } else {
            $say('robots.txt: наш - ' . ($saved ? 'сохранённых прежних несколько (' . implode(', ', array_map('basename', $saved)) . '), ' : '')
                . 'положу стоковый ocStore 3.0.3.7, который лежал до нас');
            $src = $stockRobots;
        }
        if ($do) {
            $ok = is_file($src) && copy($src, $rb) && md5_file($src) === md5_file($rb);
            $say('  сделано: ' . ($ok ? 'robots.txt прежний' : 'НЕ ВЫШЛО'));
            // Сохранённая копия делалась для нашей замены и теперь
            // совпадает с robots.txt байт в байт - до нас её не было.
            if ($ok && $src !== $stockRobots) {
                @unlink($src);
            }
        }
    }
    foreach ($rootLeftovers() as $f) {
        $say('остаток: ' . str_replace(array($site . '/', $home . '/'), array('сайт/', '~/'), $f) . ' - удалю');
        if ($do) {
            $rmTree($f);
        }
    }
};

// ==========================================================================
//  Режимы
// ==========================================================================
if ($mode === 'pokaz' || $mode === 'itog') {
    echo $mode === 'pokaz' ? "-- otkat: показ, ничего не меняю\n" : "-- otkat: итог\n";
    $active = $setting('theme_default_directory');
    $tpl = 0;
    foreach (array('common/header', 'common/footer', 'common/home', 'product/category', 'product/product',
                   'checkout/cart', 'information/contact') as $t) {
        $tpl += is_file($site . "/catalog/view/theme/$OLD_THEME/template/$t.twig") ? 1 : 0;
    }
    $say("тема сейчас: $active; прежняя $OLD_THEME: главных шаблонов $tpl из 7");
    $say('ЧПУ: ' . $setting('config_seo_url') . '; товаров включено ' . $one("SELECT COUNT(*) FROM `{$p}product` WHERE status = 1")
        . ', разделов включено ' . $one("SELECT COUNT(*) FROM `{$p}category` WHERE status = 1")
        . ', кабинетов ' . $one("SELECT COUNT(*) FROM `{$p}customer`") . ', заказов ' . $one("SELECT COUNT(*) FROM `{$p}order`"));
    if ($mode === 'pokaz') {
        foreach ($ORDER as $b) {
            $blocks[$b](false);
        }
        $filesPlan(false);
        $showSettings();
        $free = @disk_free_space($home);
        $say('место в домашней папке: ' . ($free === false ? 'не узнать' : round($free / 1048576) . ' МБ'));
    } else {
        $left = array();
        foreach ($OURS as $t) {
            if ($exists($t)) {
                $left[] = $t;
            }
        }
        $say('наши таблицы в базе: ' . ($left ? implode(', ', $left) : 'нет'));
        $files = array();
        foreach ($FILES as $f) {
            if ($f === '.htaccess') {
                if (is_file($site . '/.htaccess') && strpos(file_get_contents($site . '/.htaccess'), 'stroigeroi-webp-avif') !== false) {
                    $files[] = '.htaccess (наш блок)';
                }
            } elseif ($f === 'robots.txt') {
                if ($isOurRobots($site . '/robots.txt')) {
                    $files[] = 'robots.txt (наш)';
                }
            } elseif (file_exists($site . '/' . $f)) {
                $files[] = $f;
            }
        }
        foreach ($rootLeftovers() as $f) {
            $files[] = str_replace(array($site . '/', $home . '/'), array('сайт/', '~/'), $f);
        }
        $say('наши файлы: ' . ($files ? implode(', ', $files) : 'нет'));
    }
    exit;
}

if ($mode === 'kopiya') {
    $dir = $home . '/sg-otkat-kopiya-' . date('Ymd-His');
    if (strpos($dir, $site . '/') === 0 || !@mkdir($dir, 0700)) {
        echo "STOP: не создать папку копии $dir - ничего не менял\n";
        exit(1);
    }
    $res = $dump($dir . '/baza.sql.gz');
    $check = $res ? $dumpComplete($dir . '/baza.sql.gz') : false;
    if (!$res || $check === false || $check !== $res[0]) {
        echo "STOP: копия базы не записалась целиком - ничего не менял\n";
        exit(1);
    }
    $list = array();
    $n = 0;
    foreach ($FILES as $f) {
        if (file_exists($site . '/' . $f)) {
            $k = $copyTree($site . '/' . $f, $dir . '/sajt/' . $f);
            if ($k < 0) {
                echo "STOP: не скопировался $f - ничего не менял\n";
                exit(1);
            }
            $n += $k;
            $list[] = 'sajt/' . $f;
        }
    }
    foreach (array_merge($rootLeftovers(), $htBak !== '' ? array($htBak) : array(), $robotsSaved()) as $f) {
        $rel = strpos($f, $site . '/') === 0 ? 'sajt/' . substr($f, strlen($site) + 1)
            : 'home/' . (strpos($f, $home . '/') === 0 ? substr($f, strlen($home) + 1) : basename($f));
        $k = $copyTree($f, $dir . '/' . $rel);
        if ($k < 0) {
            echo "STOP: не скопировался $f - ничего не менял\n";
            exit(1);
        }
        $n += $k;
        $list[] = $rel;
    }
    file_put_contents($dir . '/spisok.txt', implode("\n", $list) . "\n");
    file_put_contents($home . '/sg-otkat-kopiya.txt', $dir . "\n");
    echo 'копия: ', str_replace($home . '/', '~/', $dir), '; база: таблиц ', $res[0], ', строк ', $res[1], ', ',
         round(filesize($dir . '/baza.sql.gz') / 1048576, 1), " МБ; файлов $n\n";
    exit;
}

if ($mode === 'tema' || $mode === 'tema-nazad') {
    $to = $mode === 'tema' ? $OLD_THEME : $OUR_THEME;
    $fromTheme = $mode === 'tema' ? $OUR_THEME : $OLD_THEME;
    if (!is_file($site . "/catalog/view/theme/$to/template/common/header.twig")) {
        echo "STOP: у темы $to нет template/common/header.twig - не переключаю\n";
        exit(1);
    }
    $now = $setting('theme_default_directory');
    if ($now === $to) {
        echo "тема: уже $to\n";
        exit;
    }
    if ($now !== $fromTheme) {
        echo "STOP: сейчас тема $now, а не $fromTheme - не переключаю\n";
        exit(1);
    }
    $q("UPDATE `{$p}setting` SET `value` = '" . $e($to) . "' WHERE store_id = 0 AND `key` = 'theme_default_directory'");
    $clearCache();
    $now = $setting('theme_default_directory');
    echo 'тема: ', $now, $now === $to ? '' : ' - НЕ ВЫШЛО', "\n";
    exit($now === $to ? 0 : 1);
}

if ($mode === 'baza') {
    echo "-- otkat: база\n";
    if ($setting('theme_default_directory') === $OUR_THEME) {
        echo "STOP: включена наша тема - сначала режим tema\n";
        exit(1);
    }
    $last = (string)@file_get_contents($home . '/sg-otkat-kopiya.txt');
    if (trim($last) === '' || !is_file(trim($last) . '/baza.sql.gz')) {
        echo "STOP: нет копии базы (режим kopiya) - без неё ничего не меняю\n";
        exit(1);
    }
    foreach ($ORDER as $b) {
        $blocks[$b](true);
    }
    $clearCache();
    echo $errors ? "ошибок SQL: $errors - пришлите снимок\n" : "база: без ошибок\n";
    exit($errors ? 1 : 0);
}

if ($mode === 'fajly') {
    echo "-- otkat: файлы\n";
    $last = (string)@file_get_contents($home . '/sg-otkat-kopiya.txt');
    if (trim($last) === '' || !is_file(trim($last) . '/spisok.txt')) {
        echo "STOP: нет копии файлов (режим kopiya) - без неё ничего не удаляю\n";
        exit(1);
    }
    $filesPlan(true);
    $clearCache();
    exit;
}

if ($mode === 'iz-kopii') {
    echo "-- otkat: возврат из копии\n";
    if ($from === '' || !is_file($from . '/baza.sql.gz') || $dumpComplete($from . '/baza.sql.gz') === false) {
        echo "STOP: в «{$from}» нет целой копии базы - ничего не менял\n";
        exit(1);
    }
    $m->query("SET SESSION sql_mode = ''");
    $gz = gzopen($from . '/baza.sql.gz', 'rb');
    $stmt = '';
    $done = 0;
    while (($line = gzgets($gz, 1 << 22)) !== false) {
        if (rtrim($line, "\r\n") === '-- ;;') {
            if (trim($stmt) !== '' && !$q($stmt)) {
                echo "  на инструкции №", $done + 1, "\n";
                break;
            }
            $done++;
            $stmt = '';
        } else {
            $stmt .= $line;
        }
    }
    gzclose($gz);
    echo "база: выполнено инструкций $done", $errors ? ", ОШИБКА - дальше не иду\n" : "\n";
    if ($errors) {
        exit(1);
    }
    // Файлы: всё, что лежит в копии, - на свои места.
    $n = 0;
    foreach (file($from . '/spisok.txt', FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES) as $rel) {
        $dst = strpos($rel, 'sajt/') === 0 ? $site . '/' . substr($rel, 5) : $home . '/' . substr($rel, 5);
        if (is_dir($from . '/' . $rel)) {
            $rmTree($dst);
        }
        $k = $copyTree($from . '/' . $rel, $dst);
        if ($k < 0) {
            echo "  не вернулся $rel\n";
            $errors++;
        } else {
            $n += $k;
        }
    }
    $clearCache();
    echo "файлов возвращено: $n", $errors ? ', с ошибками' : '', "\n";
    exit($errors ? 1 : 0);
}
