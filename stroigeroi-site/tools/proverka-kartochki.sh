# Карточка товара на живом сайте — только читает. Показывает цену в разметке
# для поисковиков (itemprop="price"), как цена записана в самой странице
# (пробел перед «руб» символом или текстом «&nbsp;») и блоки чужой разметки
# на странице: классы стандартной темы и модулей, которых наша тема не
# оформляет (product-thumb, list-group, panel, «вы смотрели» matrosite_looked).
( echo "-- product"; P=$(curl -s https://stroigeroi.ru/otvertka-denzel-3-6v-lii-ion-1-3ach-s-aksessuarami-csl-3-6-01); echo "microdata: $(printf %s "$P" | grep -o 'itemprop="price" content="[^"]*"' | head -1)"; echo "price text: $(printf %s "$P" | grep -oE '[0-9][0-9 ]*,[0-9]{2}[^<"]{0,14}' | head -1)"; echo "foreign blocks:"; printf %s "$P" | grep -oE 'class="(product-thumb|caption|button-group|list-group[^"]*|panel[^"]*|col-[a-z]+-[0-9]+[^"]*|[^"]*looked[^"]*|[^"]*matrosite[^"]*)"' | sort | uniq -c | sort -rn | head -10 )
