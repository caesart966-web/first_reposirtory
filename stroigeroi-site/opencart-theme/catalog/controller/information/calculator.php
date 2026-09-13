<?php
/**
 * Калькулятор материалов.
 *
 * Своя страница: у OpenCart такой нет, а текстовой страницей её не сделать -
 * калькулятор считает в браузере и живёт в разметке, а не в тексте.
 *
 * Контроллер тонкий нарочно: он только собирает страницу из общих частей.
 * Вся арифметика - в app.js, и считает она ТОЛЬКО по числам, которые ввёл
 * человек. Ни одного "среднего расхода от производителя" в неё не зашито:
 * расход краски и вес мешка человек берёт с упаковки, и подставлять за него
 * правдоподобные цифры значит отвечать за чужой перерасход.
 */
class ControllerInformationCalculator extends Controller {
	public function index() {
		$this->load->language('information/contact');

		$title = 'Калькулятор материалов';

		$this->document->setTitle($title . ' — ' . $this->config->get('config_name'));
		$this->document->setDescription('Посчитайте, сколько нужно материала на комнату: площадь стен и пола, обои, краска, плитка, ламинат, штукатурка, стяжка.');

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
