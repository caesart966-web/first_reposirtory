// Словарь категорий кэшбэка: одно каноническое название и одна иконка
// на всё, как категорию ни назвал банк. Именно так «Кафе», «Рестораны»
// и «Кафе и рестораны» с разных скринов сходятся в одну строку.
//
// Правила идут сверху вниз, побеждает первое совпадение — поэтому узкие
// («фастфуд», «доставка еды», «автоуслуги») стоят выше широких («кафе»,
// «дом и ремонт»). Строка проверяется уже нормализованной: строчные,
// «ё» → «е», знаки препинания → пробелы.
//
// name: null — название оставить, как у банка, а дать только иконку
// (бренды-партнёры: «Перекрёсток», «Ozon»…).
//
// icon — имя иконки из lucide-static (https://lucide.dev, лицензия ISC).
// Новая иконка берётся из того же набора: иначе толщина и стиль поплывут.

export const CATEGORIES = [
  { name: 'Фастфуд', icon: 'hamburger', match: [/фаст ?фуд/, /fast ?food/, /бургер/, /быстр\w* питан/] },
  { name: 'Доставка еды', icon: 'bike', match: [/доставк\w* (еды|из ресторан|готов)/] },
  { name: 'Кофейни', icon: 'coffee', match: [/кофе/] },
  { name: 'Пекарни', icon: 'croissant', match: [/пекар/, /выпечк/, /кондитер/] },
  { name: 'Кафе и рестораны', icon: 'utensils', match: [/ресторан/, /\bкафе\b/, /общепит/] },
  { name: 'Бары', icon: 'martini', match: [/\bбары?\b/, /\bпабы?\b/] },
  { name: 'Супермаркеты', icon: 'shopping-basket', match: [/супермаркет/, /гипермаркет/, /продукт/, /^еда$/, /магазин\w* у дома/] },
  { name: 'Автоуслуги', icon: 'wrench', match: [/авто ?(услуг|запчаст|сервис|товар|мойк)/, /шиномонтаж/, /ремонт авто/, /\bсто\b/] },
  { name: 'Аренда авто', icon: 'key-round', match: [/(аренд|прокат)\w* (авто|машин)/] },
  { name: 'Каршеринг', icon: 'car', match: [/каршер/, /car ?shar/] },
  { name: 'Самокаты', icon: 'scooter', match: [/самокаты/, /электросамокат/, /кикшер/] },
  { name: 'Платные дороги', icon: 'route', match: [/платн\w* дорог/] },
  { name: 'Парковки', icon: 'square-parking', match: [/парков/] },
  { name: 'АЗС', icon: 'fuel', match: [/\bазс\b/, /топлив/, /бензин/, /заправ/] },
  { name: 'Такси', icon: 'car-taxi-front', match: [/такси/] },
  { name: 'Ж/д билеты', icon: 'train-front', match: [/\bж ?д\b/, /\bжд\b/, /поезд/, /\bржд\b/, /железнодор/] },
  { name: 'Авиабилеты', icon: 'plane', match: [/авиа/, /самолет/, /перелет/] },
  { name: 'Отели', icon: 'bed-double', match: [/отел/, /гостиниц/, /прожив/] },
  { name: 'Путешествия', icon: 'luggage', match: [/путешеств/, /туризм/, /турагент/, /\bтуры?\b/, /travel/] },
  { name: 'Транспорт', icon: 'tram-front', match: [/транспорт/, /метро/, /автобус/, /проезд/] },
  { name: 'Аптеки', icon: 'pill', match: [/аптек/, /лекарств/] },
  { name: 'Медицина', icon: 'stethoscope', match: [/медиц/, /клиник/, /здоров/, /стоматол/, /врач/, /анализ/] },
  { name: 'Оптика', icon: 'glasses', match: [/оптик/, /\bочки\b/] },
  { name: 'Косметика', icon: 'sparkles', match: [/космет/, /парфюм/, /\bдухи\b/] },
  { name: 'Красота', icon: 'scissors', match: [/красот/, /салон/, /парикмах/, /маникюр/, /барбер/] },
  { name: 'Одежда и обувь', icon: 'shirt', match: [/одежд/, /обув/, /\bмода\b/, /fashion/] },
  { name: 'Спорт', icon: 'dumbbell', match: [/спорт/, /фитнес/] },
  { name: 'Детские товары', icon: 'baby', match: [/детск/, /\bдети\b/, /для детей/, /игрушк/] },
  { name: 'Игры', icon: 'gamepad-2', match: [/\bигр/, /gam(e|ing)/] },
  { name: 'Кино', icon: 'clapperboard', match: [/кино/] },
  { name: 'Развлечения', icon: 'party-popper', match: [/развлеч/, /досуг/, /аттракц/] },
  { name: 'Искусство', icon: 'palette', match: [/искусств/, /хобби/, /творч/] },
  { name: 'Театры', icon: 'drama', match: [/театр/] },
  { name: 'Музеи', icon: 'landmark', match: [/музе/, /выставк/] },
  { name: 'Концерты', icon: 'ticket', match: [/концерт/] },
  { name: 'Культура', icon: 'drama', match: [/культур/] },
  { name: 'Музыка', icon: 'music', match: [/музык/] },
  { name: 'Книги', icon: 'book-open', match: [/книг/] },
  { name: 'Образование', icon: 'graduation-cap', match: [/образован/, /обучен/, /\bкурсы\b/, /учеб/] },
  { name: 'Мебель', icon: 'sofa', match: [/мебел/] },
  { name: 'Бытовая техника', icon: 'refrigerator', match: [/бытов\w* техн/] },
  { name: 'Электроника', icon: 'smartphone', match: [/электрон/, /гаджет/, /\bтехника\b/] },
  { name: 'Цифровые сервисы', icon: 'monitor-play', match: [/цифров/, /подписк/, /онлайн ?(кино|сервис)/, /стриминг/] },
  { name: 'Связь', icon: 'signal', match: [/связь/, /мобильн/, /сотов/, /интернет/, /телеком/] },
  { name: 'ЖКХ', icon: 'zap', match: [/\bжку\b/, /\bжкх\b/, /коммунал/] },
  { name: 'Дом и ремонт', icon: 'hammer', match: [/ремонт/, /строит/, /стройматер/, /для дома/, /дом и/, /хозтовар/] },
  { name: 'Дача и сад', icon: 'sprout', match: [/\bсад/, /\bдач/, /огород/, /растен/] },
  { name: 'Животные', icon: 'paw-print', match: [/живот/, /\bзоо/, /питом/, /ветерин/] },
  { name: 'Цветы', icon: 'flower-2', match: [/^цвет(ы|оч)/, /\bцветы\b/] },
  { name: 'Ювелирные изделия', icon: 'gem', match: [/ювелир/, /украшен/] },
  { name: 'Подарки', icon: 'gift', match: [/подар/, /сувенир/] },
  { name: 'Фото и видео', icon: 'camera', match: [/фото/] },
  { name: 'Алкоголь', icon: 'wine', match: [/алкогол/, /\bвин(о|а)\b/] },
  { name: 'Страхование', icon: 'shield', match: [/страхов/] },
  { name: 'Госуслуги', icon: 'landmark', match: [/госуслуг/, /налог/, /штраф/] },
  { name: 'Маркетплейсы', icon: 'package', match: [/маркетплейс/] },
  { name: 'Все покупки', icon: 'wallet', match: [/вс[её]? покупк/, /^на вс[её]$/, /прочие покупки/, /любые покупки/, /остальн/] },
  // Бренды-партнёры: название — как у банка, иконка — по смыслу.
  { name: null, icon: 'package', match: [/\bozon\b/, /\bозон\b/, /wildberries/, /вайлдберриз/, /\bwb\b/, /яндекс ?маркет/, /мегамаркет/, /\bavito\b/, /авито/] },
  { name: null, icon: 'shopping-basket', match: [/пятерочк/, /перекрест/, /магнит/, /вкусвилл/, /\bлента\b/, /ашан/, /самокат/, /купер/, /окей/, /дикси/] },
];

export const FALLBACK_ICON = 'tag';

// \b в JS знает только латиницу: между пробелом и «б» границы слова для него
// нет, и /\bбары\b/ не находил «бары» никогда. Поэтому каждый \b в правилах
// заменяется настоящей границей по буквам Юникода.
const B = '(?:(?<![\\p{L}\\p{N}])(?=[\\p{L}\\p{N}])|(?<=[\\p{L}\\p{N}])(?![\\p{L}\\p{N}]))';
for (const c of CATEGORIES) c.match = c.match.map((re) => new RegExp(re.source.replaceAll('\\b', B), 'u'));

export function normalize(s) {
  return String(s)
    .toLowerCase()
    .replace(/ё/g, 'е')
    .replace(/[«»"“”„.,;:!?()/\\&+–—-]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

// → { name, icon, key, known }. key — то, по чему склеиваются дубли.
// Если строка попала в две разные категории («Игры и подписки», «Фастфуд
// и кофейни»), название остаётся банковским: каноническое съело бы половину.
export function resolveCategory(raw, override = {}) {
  const n = normalize(raw);
  const hits = CATEGORIES.filter((c) => c.match.some((re) => re.test(n)));
  const named = new Set(hits.filter((c) => c.name).map((c) => c.name));
  const c = hits[0];
  if (c && named.size <= 1) {
    const name = override.label ?? c.name ?? tidy(raw);
    return { name, icon: override.icon ?? c.icon, key: c.name ? normalize(c.name) : n, known: true };
  }
  const name = override.label ?? tidy(raw);
  return { name, icon: override.icon ?? c?.icon ?? FALLBACK_ICON, key: n, known: Boolean(c || override.icon) };
}

// «СУПЕРМАРКЕТЫ» со скрина → «Супермаркеты»; «Ozon» оставить как есть.
function tidy(raw) {
  const s = String(raw).trim().replace(/\s+/g, ' ');
  if (s === s.toUpperCase() && /[а-яё]{3}/i.test(s)) return s[0] + s.slice(1).toLowerCase();
  return s;
}
