<?php
/**
 * Приём заявок с сайта на своём хостинге.
 *
 * Зачем свой обработчик: зарубежные сервисы приёма форм (Web3Forms и похожие)
 * из России без VPN не открываются — заявки просто не доходили бы. Этот файл
 * лежит на том же домене, что и сайт, поэтому блокировки его не касаются.
 *
 * Требуется обычный хостинг с PHP (Beget, Timeweb, REG.RU и подобные).
 * На GitHub Pages PHP не выполняется — там форма показывает посетителю
 * прямые каналы связи (телефон, WhatsApp, Telegram) и сохраняет заявку
 * в резервную копию браузера.
 *
 * ЧТО ЗАПОЛНИТЬ ПЕРЕД ЗАЛИВКОЙ НА ХОСТИНГ — четыре строки ниже.
 */

// Куда приходят заявки. Можно несколько адресов через запятую.
const MAIL_TO = 'bagishevdelo@inbox.ru';

// От кого уходит письмо. ОБЯЗАТЕЛЬНО адрес на домене сайта, иначе почта
// сочтёт письмо подделкой и отправит в спам: у чужого домена не сойдётся SPF.
// Ящик вида zayavka@ваш-домен.ru заводится в панели хостинга за минуту.
const MAIL_FROM = 'zayavka@example.ru';

// Тот же токен, что в PUBLIC_LEAD_TOKEN при сборке сайта. Секретом он не
// является — лежит в коде страницы, — но отсекает ботов, которые долбят
// формы наугад, не читая разметку.
const FORM_TOKEN = 'norma-lead';

// Домен сайта. Запросы с других адресов не принимаем: так чужая страница
// не сможет слать заявки от вашего имени. Пустая строка отключает проверку.
const ALLOWED_HOST = '';

// Не больше стольких заявок с одного адреса за час.
const RATE_LIMIT = 10;

// Резервный журнал заявок: каждая заявка дописывается сюда ещё ДО отправки
// письма, поэтому при сбое почты ничего не теряется. Файл лежит рядом и
// закрыт от чтения из браузера файлом .htaccess (для nginx-хостинга закройте
// путь /api/ в панели — см. инструкцию в корне проекта).
const LEADS_LOG = __DIR__ . '/leads.jsonl';

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
    $file = sys_get_temp_dir() . '/norma-leads-' . date('YmdH') . '-' . md5(client_ip()) . '.count';
    $count = is_file($file) ? (int) file_get_contents($file) : 0;
    if ($count >= RATE_LIMIT) {
        return true;
    }
    file_put_contents($file, (string) ($count + 1), LOCK_EX);
    return false;
}

/** Дописывает заявку в резервный журнал. Сбой журнала заявку не блокирует. */
function log_lead(string $subject, string $message, string $replyTo): void
{
    $line = json_encode([
        'received' => date('c'),
        'ip' => client_ip(),
        'subject' => $subject,
        'replyto' => $replyTo,
        'message' => $message,
    ], JSON_UNESCAPED_UNICODE);
    if ($line !== false) {
        @file_put_contents(LEADS_LOG, $line . "\n", FILE_APPEND | LOCK_EX);
    }
}

/**
 * Отправка. В режиме проверки письмо не уходит, а пишется в файл — так можно
 * убедиться, что обработчик собирает письмо правильно, не рассылая почту:
 * NORMA_MAIL_DRY_RUN=/tmp/lead.eml php -S 127.0.0.1:8000 -t dist
 */
function deliver(string $to, string $subject, string $body, array $headers): bool
{
    $dry = getenv('NORMA_MAIL_DRY_RUN');
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

// Сначала журнал, потом почта: при сбое почты заявка остаётся в журнале.
log_lead($subject, $message, $replyTo);

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
