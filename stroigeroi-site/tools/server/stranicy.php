<?php
/*
  Серверная часть правки 21: страницы. Команда из сообщения заказчику
  снимает curl'ом главную, раздел, товар и контакты уже после правки
  и базы, а этот файл их читает. Только читает; через сайт не работает.

  -- check    на каждой странице: сколько раз старый номер, сколько новый,
              сколько заготовок макета (класс ph); ждём 0 / больше 0 / 0
  -- blocks   все блоки OCFilter на странице раздела
  -- markup   дерево #ocfilter: теги, id, классы, data-атрибуты; одинаковых
              соседей по два, остальные - «... +N more»; до 120 строк
  -- classes  все классы внутри фильтра и сколько раз каждый
  -- script   встроенный скрипт запуска фильтра, до 45 строк

  Первая версия разведки (23.09) брала первый блок OCFilter на странице,
  и им оказалась пустая мобильная обёртка (её наполняет скрипт);
  теперь берётся #ocfilter.

  Запуск: php stranicy.php <папка со снятыми страницами>
*/
if (PHP_SAPI !== 'cli') {
    exit;
}
$dir = isset($argv[1]) ? rtrim($argv[1], '/') : '.';

echo "-- check\n";
foreach (array('glavnaya', 'razdel', 'tovar', 'kontakty') as $name) {
    $f = "$dir/$name.html";
    $h = is_file($f) ? file_get_contents($f) : '';
    if ($h === '') {
        echo "$name: страница не открылась\n";
        continue;
    }
    $old = preg_match_all('/963\D{0,8}830\D{0,8}09\D{0,8}99/', $h);
    $new = preg_match_all('/963\D{0,8}831\D{0,8}99\D{0,8}99/', $h);
    $ph = preg_match_all('/class="(?:[^"]*\s)?ph(?:\s[^"]*)?"/', $h);
    echo "$name: old number $old, new number $new, placeholders $ph\n";
}

$f = "$dir/razdel.html";
if (!is_file($f)) {
    exit;
}
libxml_use_internal_errors(true);
$d = new DOMDocument();
$d->loadHTML('<?xml encoding="utf-8"?>' . file_get_contents($f));
$x = new DOMXPath($d);
$o = '(contains(@id,"ocf") or contains(@class,"ocf"))';

echo "-- blocks\n";
$root = $x->query('//*[@id="ocfilter"]')->item(0);
$pick = null;
$best = -1;
foreach ($x->query("//*[$o][not(ancestor::*[$o])]") as $el) {
    $n = $x->query('.//*', $el)->length;
    echo $el->nodeName, '#', $el->getAttribute('id'), ' .', $el->getAttribute('class'), ' : ', $n, " inside\n";
    if ($n > $best) {
        $best = $n;
        $pick = $el;
    }
}
if (!$root) {
    $root = $pick;
}
if (!$root) {
    echo "no ocfilter block\n";
    exit;
}

echo "-- markup\n";
$lines = 0;
$key = function ($c) {
    return $c->nodeName . '.' . trim(preg_replace('/\s+/', '.', $c->getAttribute('class')));
};
$walk = function ($node, $depth) use (&$walk, &$lines, $key) {
    $total = array();
    $seen = array();
    foreach ($node->childNodes as $c) {
        if ($c->nodeType == XML_ELEMENT_NODE) {
            $k = $key($c);
            $total[$k] = isset($total[$k]) ? $total[$k] + 1 : 1;
        }
    }
    foreach ($node->childNodes as $c) {
        if ($lines >= 120) {
            return;
        }
        $pad = str_repeat('  ', $depth);
        if ($c->nodeType == XML_TEXT_NODE) {
            $t = trim(preg_replace('/\s+/u', ' ', $c->textContent));
            if ($t !== '') {
                echo $pad, '"', mb_substr($t, 0, 40), "\"\n";
                $lines++;
            }
            continue;
        }
        if ($c->nodeType != XML_ELEMENT_NODE) {
            continue;
        }
        $k = $key($c);
        $seen[$k] = isset($seen[$k]) ? $seen[$k] + 1 : 1;
        if ($seen[$k] > 2) {
            if ($seen[$k] == 3) {
                echo $pad, '... +', $total[$k] - 2, ' more ', $k, "\n";
                $lines++;
            }
            continue;
        }
        if (in_array($c->nodeName, array('script', 'style', 'svg'))) {
            echo $pad, '<', $c->nodeName, ">\n";
            $lines++;
            continue;
        }
        $s = rtrim($c->nodeName . ($c->getAttribute('id') !== '' ? '#' . $c->getAttribute('id') : '') . substr($k, strlen($c->nodeName)), '.');
        $extra = '';
        foreach ($c->attributes as $a) {
            $an = $a->nodeName;
            if (in_array($an, array('type', 'name', 'value', 'for', 'style', 'href', 'checked', 'disabled')) || strpos($an, 'data-') === 0) {
                $extra .= ' ' . $an . ($an == 'href' ? '' : '=' . mb_substr($a->nodeValue, 0, 24));
            }
        }
        echo mb_substr($pad . $s . $extra, 0, 220), "\n";
        $lines++;
        $walk($c, $depth + 1);
    }
};
echo $root->nodeName, '#', $root->getAttribute('id'), ' .', $root->getAttribute('class'), "\n";
$walk($root, 1);

echo "-- classes\n";
$cnt = array();
foreach ($x->query('.//*[@class]', $root) as $el) {
    foreach (preg_split('/\s+/', trim($el->getAttribute('class'))) as $c) {
        $cnt[$c] = isset($cnt[$c]) ? $cnt[$c] + 1 : 1;
    }
}
arsort($cnt);
$out = '';
foreach ($cnt as $c => $v) {
    $out .= $c . '*' . $v . ' ';
}
echo wordwrap(trim($out), 140), "\n";

echo "-- script\n";
$sl = 0;
foreach ($x->query('//script[not(@src)]') as $s) {
    if (strpos($s->textContent, 'ocfilter') === false) {
        continue;
    }
    foreach (preg_split('/\r?\n/', $s->textContent) as $l) {
        $l = trim($l);
        if ($l === '' || $l === '<!--' || $l === '//-->' || $l === '//--></script>') {
            continue;
        }
        if ($sl++ >= 45) {
            echo "...\n";
            break 2;
        }
        echo mb_substr($l, 0, 140), "\n";
    }
}
