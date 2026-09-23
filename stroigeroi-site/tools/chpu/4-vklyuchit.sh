# Включает человекопонятные адреса (config_seo_url = 1) и сразу проверяет сайт.
# Движок — обычный, не SeoPro (config_seo_pro остаётся 0): он переписывает
# только ссылки на товары, разделы, статьи и производителей, а корзина,
# кабинет и оформление заказа остаются на index.php?route=... — правила
# robots.txt и запрет регистрации в .htaccess для них работают как раньше.
# SeoPro ещё и перенаправляет старые адреса на новые, а в теме есть ссылки,
# вписанные в шаблон как index.php?route=...: каждая стала бы лишним
# переходом, дорогим при пинге до Камчатки.
#
# Как проверяет: собирает внутренние ссылки главной, двух разделов и корзины
# (до 150), открывает каждую и считает те, что не открылись. Делает это до
# включения и после. Стало больше неоткрывающихся — выключает адреса обратно
# и пишет ROLLBACK со списком. Уже битые до включения ссылки отката не
# вызывают. Сайт не ответил до включения — STOP, ничего не меняется.
# Проверено на копии таблиц и подставном сайте: рабочий сайт, сломанные
# короткие адреса (откат), недоступный сайт (остановка).
( cd /var/www/u2934771/data/www/stroigeroi.ru || exit 1; S=https://stroigeroi.ru; seo() { php -r 'mysqli_report(MYSQLI_REPORT_OFF); include "config.php"; $m = @new mysqli(DB_HOSTNAME, DB_USERNAME, DB_PASSWORD, DB_DATABASE, (int)DB_PORT); if ($m->connect_error) { echo "DB: ", $m->connect_error, "\n"; exit(1); } $v = (int)$argv[1]; $ok = $m->query("UPDATE " . DB_PREFIX . "setting SET value = \"$v\" WHERE store_id = 0 AND `key` = \"config_seo_url\"") && $m->affected_rows >= 0; $r = $m->query("SELECT value FROM " . DB_PREFIX . "setting WHERE store_id = 0 AND `key` = \"config_seo_url\""); $now = $r ? $r->fetch_row() : null; echo "config_seo_url = ", ($now ? $now[0] : "?"), "\n"; exit(($ok && $now && (int)$now[0] === $v) ? 0 : 1);' "$1"; }; links() { for p in "" elektrika-i-svet pylesosy-stroitelnye "index.php?route=checkout/cart"; do curl -s --max-time 20 "$S/$p"; done | grep -oE 'href="[^"#]+' | cut -c7- | sed 's/&amp;/\&/g' | awk -v S="$S" '/^(tel|mailto|javascript):/ {next} /^https?:\/\// { if (index($0, S "/") == 1) print; next } /^\// { print S $0; next } { print S "/" $0 }' | grep -vE '\.(css|js|png|jpe?g|gif|webp|avif|svg|ico|woff2?|xml|pdf)(\?|$)' | sort -u | head -150; }; bad() { echo "$1" | xargs -d '\n' -P 4 -I{} curl -s -o /dev/null --max-time 20 -w '%{http_code} {}\n' '{}' | grep -vE '^[23][0-9]{2} '; }; B=$(links); BN=$(echo "$B" | grep -c .); if [ "$BN" -lt 10 ]; then echo "STOP: site did not answer ($BN links), nothing changed"; exit 1; fi; BX=$(bad "$B"); BF=$(printf '%s' "$BX" | grep -c .); echo "before: $BN links, $BF not opening"; seo 1 || exit 1; A=$(links); AN=$(echo "$A" | grep -c .); AX=$(bad "$A"); AF=$(printf '%s' "$AX" | grep -c .); OLD=$(echo "$A" | grep -cE 'route=product/(category|product)'); echo "after: $AN links, $AF not opening, old-style catalog links: $OLD"; if [ "$AN" -lt 10 ] || [ "$AF" -gt "$BF" ]; then printf '%s\n' "$AX" | head -10; seo 0; echo "ROLLBACK: pretty URLs are off again"; else M=$(curl -s --max-time 60 "$S/index.php?route=extension/feed/google_sitemap" | grep -o '<loc>[^<]*'); echo "sitemap: $(echo "$M" | grep -c .) urls, $(echo "$M" | grep -c 'index.php') old-style"; echo "OK: pretty URLs are on"; fi )
