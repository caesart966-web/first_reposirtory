<?php
/**
 * Строительный калькулятор (14 расчётов, javascript/calc.js).
 *
 * Своя страница: у OpenCart такой нет, а текстовой страницей её не сделать -
 * калькулятор считает в браузере и живёт в разметке, а не в тексте.
 *
 * Контроллер тонкий нарочно: он только собирает страницу из общих частей.
 * Вся арифметика - в javascript/calc.js, и считает она по числам на форме:
 * размеры вписывает человек, а допущения (шаг стоек, длина профиля, запас)
 * стоят в полях и меняются. Ни одного "среднего расхода от производителя"
 * в неё не зашито: расход краски и вес мешка человек берёт с упаковки,
 * мощность секции радиатора - из паспорта, и подставлять за него
 * правдоподобные цифры значит отвечать за чужой перерасход.
 */
class ControllerInformationCalculator extends Controller {
	public function index() {
		$this->load->language('information/contact');

		$title = 'Строительный калькулятор';

		$this->document->setTitle($title . ' — ' . $this->config->get('config_name'));
		// Описание - только про то, что на странице есть: 14 калькуляторов
		// из javascript/calc.js. Появится новый - дописать и сюда.
		$this->document->setDescription('14 строительных калькуляторов: гипсокартон и перегородки, смеси, краска, обои, плитка, ламинат, потолок «Армстронг», панели, кирпич, бетон, утеплитель, кровля и радиаторы.');

		$data['heading_title'] = $title;

		$data['breadcrumbs'] = array();

		$data['breadcrumbs'][] = array(
			'text' => $this->language->get('text_home'),
			'href' => $this->url->link('common/home')
		);

		$data['breadcrumbs'][] = array(
			'text' => $title,
			'href' => $this->url->link('information/calculator')
		);

		$data['column_left'] = $this->load->controller('common/column_left');
		$data['column_right'] = $this->load->controller('common/column_right');
		$data['content_top'] = $this->load->controller('common/content_top');
		$data['content_bottom'] = $this->load->controller('common/content_bottom');
		$data['footer'] = $this->load->controller('common/footer');
		$data['header'] = $this->load->controller('common/header');

		$this->response->setOutput($this->load->view('information/calculator', $data));
	}
}
