// Динамические строки в формах: ДС, виды работ, доводы. Без зависимостей.
document.addEventListener('click', function (e) {
  var btn = e.target.closest('[data-add]');
  if (!btn) return;
  var kind = btn.getAttribute('data-add');
  var box = document.getElementById(kind);
  var counter = document.getElementById(kind + '_n');
  var i = parseInt(counter.value || '0', 10);
  var div = document.createElement('div');
  if (kind === 'addenda') {
    div.className = 'row4';
    div.innerHTML = '<input name="add_number_' + i + '" placeholder="№"><input type="date" name="add_date_' + i + '"><input name="add_price_' + i + '" placeholder="новая цена, ₽"><input name="add_note_' + i + '" placeholder="что меняет">';
  } else if (kind === 'works') {
    div.className = 'row4';
    div.innerHTML = '<input name="work_name_' + i + '" placeholder="наименование"><input name="work_amount_' + i + '" placeholder="сумма, ₽"><input name="work_source_' + i + '" placeholder="источник"><select name="work_human_' + i + '"><option value="">по Перечню</option><option value="sro">СРО (решил человек)</option><option value="nosro">не СРО (решил человек)</option></select>';
  } else if (kind === 'claims') {
    var tpl = document.getElementById('claim-tpl');
    div.innerHTML = tpl.innerHTML.replace(/_N"/g, '_' + i + '"');
    div = div.firstElementChild;
  }
  box.appendChild(div);
  counter.value = i + 1;
});
