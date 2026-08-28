<?php
/**
 * Приём заявок с сайта на своей же площадке.
 *
 * Зачем: раньше форма уходила в Web3Forms — зарубежный сервис, который из
 * России без VPN не открывается, и заявки просто не доходили бы. Этот файл
 * лежит на том же домене, что и сайт, поэтому блокировки его не касаются:
 * браузер посетителя никуда наружу не ходит.
 *
 * Формат запроса и ответа намеренно повторяет Web3Forms — фронтенд менять
 * не пришлось, в сборке меняется только адрес: VITE_LEAD_ENDPOINT.
 *
 * Требуется обычный хостинг с PHP (Beget, Timeweb, REG.RU и подобные).
 * На объектном хранилище без PHP этот способ не работает.
 *
 * ЧТО НУЖНО ЗАПОЛНИТЬ ПЕРЕД ЗАЛИВКОЙ — три строки ниже.
 */

// Куда приходят заявки. Можно несколько адресов через запятую.
const MAIL_TO = '9001330219@mail.ru';

// От кого уходит письмо. ОБЯЗАТЕЛЬНО адрес на домене сайта, иначе почта
// получателя сочтёт письмо подделкой и отправит в спам: у чужого домена
// не сойдётся SPF. Ящик заводится в панели хостинга за минуту.
const MAIL_FROM = 'zayavka@example.ru';

// Тот же токен, что в VITE_LEAD_ACCESS_KEY при сборке сайта. Секретом он не
// является — лежит в коде страницы, — но отсекает ботов, которые долбят
// формы наугад, не читая разметку.
const FORM_TOKEN = 'change-me';

// Домен сайта. Запросы с других адресов не принимаем: так чужая страница
// не сможет слать заявки от вашего имени. Пустая строка отключает проверку.
const ALLOWED_HOST = '';

// Не больше стольких заявок с одного адреса за час.
const RATE_LIMIT = 10;

// --- дальше править не нужно ---------------------------------------------

const MAX_FIELD = 200;
const MAX_MESSAGE = 4000;

header('Content-Type: application/json; charset=utf-8');
header('X-Content-Type-Options: nosniff');

function fail(int $code, string $message): never
{
    http_response_code($code);
    echo json_encode(['success' => false, 'message' => $message], JSON_UNESCAPED_UNICODE);
    exit;
}

/** Убирает переводы строк: без этого в заголовки письма можно дописать чужие. */
function header_safe(string $value, int $limit = MAX_FIELD): string
{
    $value = str_replace(["\r", "\n", "\0"], ' ', $value);
    return mb_substr(trim($value), 0, $limit);
}

/** Тема письма по-русски: без кодирования почтовые клиенты покажут кракозябры. */
function encode_subject(string $subject): string
{
    return '=?UTF-8?B?' . base64_encode($subject) . '?=';
}

function client_ip(): string
{
    return (string) ($_SERVER['REMOTE_ADDR'] ?? 'unknown');
}

/** Простое ограничение частоты: счётчик на час в файле во временной папке. */
function rate_limited(): bool
{
    $file = sys_get_temp_dir() . '/sro-leads-' . date('YmdH') . '-' . md5(client_ip()) . '.count';
    $count = is_file($file) ? (int) file_get_contents($file) : 0;
    if ($count >= RATE_LIMIT) {
        return true;
    }
    file_put_contents($file, (string) ($count + 1), LOCK_EX);
    return false;
}

/**
 * Отправка. В режиме проверки письмо не уходит, а пишется в файл — так можно
 * убедиться, что обработчик собирает письмо правильно, не рассылая почту.
 */
function deliver(string $to, string $subject, string $body, array $headers): bool
{
    $dry = getenv('SRO_MAIL_DRY_RUN');
    if ($dry) {
        $dump = "To: $to\n" . implode("\n", $headers) . "\nSubject: $subject\n\n$body\n";
        return (bool) file_put_contents($dry, $dump);
    }

    // Пятый параметр задаёт конверт отправителя — по нему принимающая сторона
    // проверяет SPF. Без него письма чаще уходят в спам.
    return mail($to, $subject, $body, implode("\r\n", $headers), '-f' . MAIL_FROM);
}

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
    fail(405, 'Метод не поддерживается');
}

if (ALLOWED_HOST !== '') {
    $origin = $_SERVER['HTTP_ORIGIN'] ?? $_SERVER['HTTP_REFERER'] ?? '';
    $host = $origin === '' ? '' : (string) parse_url($origin, PHP_URL_HOST);
    if ($host !== ALLOWED_HOST) {
        fail(403, 'Запрос не с сайта');
    }
}

$raw = file_get_contents('php://input');
if ($raw === false || strlen($raw) > 16384) {
    fail(400, 'Пустой или слишком большой запрос');
}

$data = json_decode($raw, true);
if (!is_array($data)) {
    fail(400, 'Ожидается JSON');
}

if (!hash_equals(FORM_TOKEN, (string) ($data['access_key'] ?? ''))) {
    fail(403, 'Неверный ключ формы');
}

$message = trim((string) ($data['message'] ?? ''));
if ($message === '') {
    fail(400, 'Пустая заявка');
}
$message = mb_substr($message, 0, MAX_MESSAGE);

$subject = header_safe((string) ($data['subject'] ?? 'Заявка с сайта'));
$fromName = header_safe((string) ($data['from_name'] ?? 'Заявка с сайта'), 100);
$replyTo = header_safe((string) ($data['replyto'] ?? ''), 254);

if ($replyTo !== '' && !filter_var($replyTo, FILTER_VALIDATE_EMAIL)) {
    $replyTo = '';
}

if (rate_limited()) {
    fail(429, 'Слишком много заявок подряд, попробуйте позже');
}

$headers = [
    'From: ' . encode_subject($fromName) . ' <' . MAIL_FROM . '>',
    'Content-Type: text/plain; charset=UTF-8',
    'Content-Transfer-Encoding: 8bit',
    'MIME-Version: 1.0',
];
if ($replyTo !== '') {
    $headers[] = 'Reply-To: ' . $replyTo;
}

// В письмо добавляем время и адрес — пригодится, если заявка спорная.
$body = $message . "\n\n---\nПолучено: " . date('d.m.Y H:i:s') . "\nIP: " . client_ip();

if (!deliver(MAIL_TO, encode_subject($subject), $body, $headers)) {
    // Молчаливого «успеха» быть не должно: посетитель увидит экран ошибки
    // с прямыми контактами и позвонит, вместо того чтобы ждать ответа.
    fail(500, 'Письмо не удалось отправить');
}

echo json_encode(['success' => true], JSON_UNESCAPED_UNICODE);
