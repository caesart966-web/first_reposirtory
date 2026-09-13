<?php
/**
 * Заказ обратного звонка.
 *
 * Обработчик формы из подвала темы stroigeroi2026. В OpenCart такой формы
 * нет, а форма обратной связи движка требует адрес электронной почты,
 * которого мы у посетителя не спрашиваем: он оставляет телефон.
 *
 * Защита здесь не паранойя. На этом же сайте с декабря 2024 года роботы
 * пользовались формой регистрации как рассыльщиком: 13 389 писем, до 814
 * в сутки в пике. Любая открытая форма, умеющая отправлять почту, будет
 * найдена и использована так же, поэтому:
 *
 *   - ловушка: поле company не видно человеку и обязано остаться пустым;
 *   - пауза: с одной сессии не чаще одного письма в 60 секунд;
 *   - согласие на обработку данных обязательно (152-ФЗ, и заодно отсекает
 *     простые сценарии автозаполнения);
 *   - имя и телефон обрезаются по длине и очищаются от переводов строки:
 *     перевод строки в теме письма позволяет дописать свои заголовки
 *     и превратить письмо в рассылку кому угодно;
 *   - отправитель письма - сам магазин (config_email), а не посетитель.
 *     У стоковой формы обратной связи движка в поле "От кого" стоит адрес
 *     посетителя: письма уходят от чужого имени, не проходят проверку SPF
 *     и попадают в спам.
 *
 * Получатель - адрес магазина из настроек (Система -> Настройки -> Почта).
 * Отдельного адреса для заявок здесь нет намеренно: вторая точка правды
 * разошлась бы с первой.
 */
class ControllerInformationCallback extends Controller {
	public function index() {
		// Прямого захода на этот адрес быть не должно: форма живёт в подвале.
		$this->response->redirect($this->url->link('common/home'));
	}

	public function send() {
		$json = array();

		$post = $this->request->post;

		$name    = isset($post['name'])    ? trim((string)$post['name'])    : '';
		$phone   = isset($post['phone'])   ? trim((string)$post['phone'])   : '';
		$consent = isset($post['consent']) ? (string)$post['consent']       : '';
		$trap    = isset($post['company']) ? trim((string)$post['company']) : '';
		// Вопрос с формы на странице контактов. У кнопки «заказать звонок»
		// этого поля нет, и тогда письмо уходит без него.
		$message = isset($post['message']) ? trim((string)$post['message']) : '';

		// Ловушка. Человек этого поля не видит и заполнить не может.
		// Молчим и делаем вид, что всё хорошо: робот не должен узнать,
		// что его распознали, иначе следующая попытка будет умнее.
		if ($trap !== '') {
			$json['success'] = true;
			$this->respond($json);
			return;
		}

		if (!empty($this->session->data['sg_callback_time'])) {
			$passed = time() - (int)$this->session->data['sg_callback_time'];

			if ($passed < 60) {
				$json['error'] = 'Заявка уже отправлена. Следующую можно оставить через минуту.';
				$this->respond($json);
				return;
			}
		}

		if (utf8_strlen($name) < 2 || utf8_strlen($name) > 64) {
			$json['error_name'] = 'Впишите имя';
		}

		// Цифр должно быть от 10 до 15: короче не бывает даже городского
		// с кодом, длиннее не бывает ни у одной страны (стандарт E.164).
		$digits = preg_replace('/\D/', '', $phone);

		if (strlen($digits) < 10 || strlen($digits) > 15) {
			$json['error_phone'] = 'Впишите номер телефона';
		}

		if ($consent !== '1') {
			$json['error_consent'] = 'Без согласия отправить нельзя';
		}

		if ($message !== '' && utf8_strlen($message) > 2000) {
			$json['error_message'] = 'Вопрос слишком длинный — уложитесь в 2000 знаков';
		}

		if (!$json) {
			// Переводы строки и возврат каретки выбрасываем до того, как
			// значение попадёт в тему письма.
			$safe_name  = str_replace(array("\r", "\n", "\t"), ' ', $name);
			$safe_phone = str_replace(array("\r", "\n", "\t"), ' ', $phone);

			$text  = ($message !== '' ? 'Вопрос с сайта.' : 'Заявка на обратный звонок с сайта.') . "\n\n";
			$text .= 'Имя: ' . $safe_name . "\n";
			$text .= 'Телефон: ' . $safe_phone . "\n";

			if ($message !== '') {
				// Текст вопроса идёт в тело письма, а не в тему: переводы
				// строки здесь безопасны и нужны, чтобы его можно было читать.
				$text .= "\nВопрос:\n" . $message . "\n";
			}

			$text .= "\n" . 'Время: ' . date('d.m.Y H:i') . "\n";
			$text .= 'Согласие на обработку персональных данных: дано.' . "\n";

			$mail = new Mail($this->config->get('config_mail_engine'));
			$mail->parameter = $this->config->get('config_mail_parameter');
			$mail->smtp_hostname = $this->config->get('config_mail_smtp_hostname');
			$mail->smtp_username = $this->config->get('config_mail_smtp_username');
			$mail->smtp_password = html_entity_decode($this->config->get('config_mail_smtp_password'), ENT_QUOTES, 'UTF-8');
			$mail->smtp_port = $this->config->get('config_mail_smtp_port');
			$mail->smtp_timeout = $this->config->get('config_mail_smtp_timeout');

			$mail->setTo($this->config->get('config_email'));
			$mail->setFrom($this->config->get('config_email'));
			$mail->setSender(html_entity_decode($this->config->get('config_name'), ENT_QUOTES, 'UTF-8'));
			$mail->setSubject(($message !== '' ? 'Вопрос с сайта: ' : 'Обратный звонок: ') . $safe_name . ', ' . $safe_phone);
			$mail->setText($text);
			$mail->send();

			$this->session->data['sg_callback_time'] = time();

			$json['success'] = true;
		}

		$this->respond($json);
	}

	private function respond($json) {
		$this->response->addHeader('Content-Type: application/json');
		$this->response->setOutput(json_encode($json));
	}
}
