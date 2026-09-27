<?php
/*
  Заявка на звонок (catalog/controller/information/callback.php) в окружении-
  заглушке: запрос чистится так же, как в OpenCart 3 (Request::clean -
  htmlspecialchars), письмо пишется в переменную вместо отправки.

  Что проверяется:
  - ссылка калькулятора на расчёт (…#armstrong?length=7&width=3) доходит
    до письма целой: письмо уходит простым текстом, и «&amp;» вместо «&»
    открывало бы расчёт без половины размеров;
  - перевод строки в имени не попадает в тему письма - иначе через неё
    дописывают свои заголовки и рассылают спам;
  - вопрос длиннее 2000 знаков отклоняется, и письмо не уходит.

  Запуск: php tools/test-callback.php
*/
if (PHP_SAPI !== 'cli') {
    exit;
}

class Controller
{
    protected $registry;
    public function __construct($registry) { $this->registry = $registry; }
    public function __get($key) { return $this->registry[$key]; }
}

function utf8_strlen($s) { return mb_strlen($s, 'UTF-8'); }

class Mail
{
    public static $sent = array();
    public $parameter, $smtp_hostname, $smtp_username, $smtp_password, $smtp_port, $smtp_timeout;
    private $data = array();
    public function __construct($engine) {}
    public function setTo($v) { $this->data['to'] = $v; }
    public function setFrom($v) { $this->data['from'] = $v; }
    public function setSender($v) { $this->data['sender'] = $v; }
    public function setSubject($v) { $this->data['subject'] = $v; }
    public function setText($v) { $this->data['text'] = $v; }
    public function send() { self::$sent[] = $this->data; }
}

class Config { public function get($key) { return $key === 'config_email' ? 'shop@example.com' : ''; } }

class Response
{
    public $output;
    public function addHeader($h) {}
    public function setOutput($o) { $this->output = $o; }
    public function redirect($url) {}
}

require __DIR__ . '/../opencart-theme/catalog/controller/information/callback.php';

$failures = 0;
$fail = function ($text) use (&$failures) {
    $failures++;
    echo 'FAIL ', $text, "\n";
};

// Один запрос к обработчику: $post - как прислал браузер.
$send = function (array $post) {
    $clean = function ($v) { return htmlspecialchars($v, ENT_COMPAT, 'UTF-8'); };
    $session = new stdClass;
    $session->data = array();
    $response = new Response;
    $before = count(Mail::$sent);
    $controller = new ControllerInformationCallback(array(
        'request' => (object)array('post' => array_map($clean, $post)),
        'session' => $session,
        'config' => new Config,
        'response' => $response,
    ));
    $controller->send();
    return array(json_decode($response->output, true), count(Mail::$sent) > $before ? end(Mail::$sent) : null);
};

$link = 'https://stroigeroi.ru/index.php?route=information/calculator#armstrong?length=7&width=3&lamps=0';
list($answer, $mail) = $send(array(
    'name' => "Иван \"Петрович\"\r\nBcc: spam@example.com",
    'phone' => '+7 963 831-99-99',
    'consent' => '1',
    'company' => '',
    'message' => "Потолок «Армстронг»: комната 7 м × 3 м\nОткрыть расчёт: $link",
));
if (empty($answer['success']) || !$mail) {
    $fail('заявка с расчётом не отправилась: ' . json_encode($answer, JSON_UNESCAPED_UNICODE));
} else {
    if (strpos($mail['text'], "Открыть расчёт: $link\n") === false) {
        $fail('ссылка на расчёт дошла до письма не целой');
    }
    if (strpos($mail['text'], '&amp;') !== false || strpos($mail['subject'], '&quot;') !== false) {
        $fail('в письме остались &amp; или &quot; - письмо простым текстом, их увидит менеджер');
    }
    if (strpbrk($mail['subject'], "\r\n") !== false) {
        $fail('перевод строки из имени попал в тему письма');
    }
    if (strpos($mail['subject'], 'Иван "Петрович"') === false) {
        $fail('имя в теме письма искажено: ' . $mail['subject']);
    }
}

list($answer, $mail) = $send(array(
    'name' => 'Иван',
    'phone' => '+7 963 831-99-99',
    'consent' => '1',
    'company' => '',
    'message' => str_repeat('а', 2001),
));
if (empty($answer['error_message']) || $mail) {
    $fail('вопрос длиннее 2000 знаков должен отклоняться без письма');
}

if ($failures) {
    exit(1);
}
echo "Заявка на звонок: ссылка на расчёт доходит целой, тема письма в одну строку, длинный вопрос отклоняется\n";
