import {
  Building2,
  FileText,
  Gavel,
  GraduationCap,
  Handshake,
  Landmark,
  ListPlus,
  Medal,
  ScrollText,
  Search,
  ShieldCheck,
  UserCheck,
  type LucideIcon,
} from 'lucide-react'
import { IMAGES } from '../content/images'
import { cardHoverStatic } from './ui/card'
import { Figure } from './ui/Figure'
import { Reveal } from './ui/Reveal'
import { Section, SectionHeading } from './ui/Section'

// Восемь равнозначных карточек читались как каша, поэтому услуги разбиты
// на две понятные группы: что делаем с самой СРО и что — со специалистами.
type ServiceGroup = {
  title: string
  items: { icon: LucideIcon; title: string; text: string }[]
}

const GROUPS: ServiceGroup[] = [
  {
    title: 'Вступление и сопровождение',
    items: [
      {
        icon: Building2,
        title: 'Вступление в СРО',
        text: 'Организую процесс от выбора СРО до внесения компании в реестр членов.',
      },
      {
        icon: Search,
        title: 'Подбор СРО',
        text: 'Сравню требования, взносы и условия — предложу варианты под вашу задачу.',
      },
      {
        icon: FileText,
        title: 'Подготовка документов',
        text: 'Соберу полный пакет и выверю каждый документ перед подачей.',
      },
      {
        icon: ShieldCheck,
        title: 'Проверка СРО',
        text: 'Проверю статус организации по открытым реестрам до оплаты взносов.',
      },
    ],
  },
  {
    title: 'Специалисты и реестры',
    // Кадр изысканий отсюда уехал в секцию «Виды СРО»: там он один из трёх
    // и работает по назначению — показывает область, — а здесь стоял рядом
    // с карточками про НРС и НОК, к которым отношения не имеет.
    items: [
      {
        icon: UserCheck,
        title: 'НРС',
        text: 'Помогу с включением специалистов в национальный реестр: требования и документы.',
      },
      {
        icon: GraduationCap,
        title: 'НОК',
        text: 'Объясню, как проходит независимая оценка квалификации, и помогу подготовиться.',
      },
      {
        icon: ListPlus,
        title: 'Расширение видов работ',
        text: 'Оформлю изменение уровня ответственности или состава видов работ.',
      },
      {
        icon: Handshake,
        title: 'Сопровождение проверок',
        text: 'Подготовлю к проверке СРО и помогу корректно ответить на запросы.',
      },
    ],
  },
]

// Смежные юридические задачи с визитки. Услуга вторичная, но «вторичная» —
// это про размер и место, а не про небрежность: раньше иконки стояли голыми
// и бледно-серыми и читались как неудавшаяся картинка. Теперь у них та же
// оправа, что у карточек услуг выше, только подложка нейтральная вместо
// акцентной — иерархия держится цветом, а не отсутствием оформления.
//
// Глифы подобраны по смыслу, а не «что-нибудь юридическое»: здание с колоннами
// — регистрирующий орган, свиток — устав, молоток — суд, медаль — аттестация.
const LEGAL = [
  {
    icon: Landmark,
    title: 'Регистрация и ликвидация',
    text: 'Юридических лиц и предпринимателей — от подачи до внесения записи.',
  },
  {
    icon: ScrollText,
    title: 'Изменения в учредительных документах',
    text: 'Подготовлю пакет и сопровожу внесение изменений в ЕГРЮЛ.',
  },
  {
    icon: Gavel,
    title: 'Представление интересов в судах',
    text: 'Досудебная работа и защита позиции компании в судебных спорах.',
  },
  {
    icon: Medal,
    title: 'Повышение квалификации и аттестации',
    text: 'Помогу организовать обучение и аттестацию специалистов для СРО и НРС.',
  },
]

export function Services() {
  return (
    <Section id="services" className="bg-neutral-50/55">
      <SectionHeading
        eyebrow="Услуги"
        title="С чем помогу"
        subtitle="Разовые задачи и полное сопровождение — в зависимости от вашей ситуации."
      />

      <div className="mt-10 space-y-10">
        {GROUPS.map((group) => (
          <div key={group.title}>
            <Reveal>
              <h3 className="text-sm font-semibold uppercase tracking-[0.16em] text-neutral-600">
                {group.title}
              </h3>
            </Reveal>
            {/* Фотографий в сетке услуг нет: обе группы — про действия, а не
                про области, и любой кадр здесь иллюстрировал бы соседнюю тему.
                Области показаны выше, в «Видах СРО», каждая своим снимком. */}
            <div className="mt-5 grid gap-4 sm:grid-cols-2 sm:gap-5 lg:grid-cols-4">
              {group.items.map((service, index) => (
                <Reveal key={service.title} delay={(index % 4) * 70} className="h-full">
                  <article
                    className={`h-full rounded-2xl border border-neutral-200 bg-white p-6 shadow-card ${cardHoverStatic}`}
                  >
                    <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-accent-50 text-accent-600">
                      <service.icon className="h-5 w-5" aria-hidden="true" />
                    </div>
                    <h4 className="mt-5 font-semibold text-neutral-950">{service.title}</h4>
                    <p className="mt-2 text-sm leading-relaxed text-neutral-600">{service.text}</p>
                  </article>
                </Reveal>
              ))}
            </div>
          </div>
        ))}
      </div>

      <Reveal className="mt-12 border-t border-neutral-200 pt-8">
        <h3 className="text-sm font-semibold uppercase tracking-[0.16em] text-neutral-600">
          Смежные юридические задачи
        </h3>
        {/* Список слева, рисунок справа, без рамки — на серой плашке
            вырезанный объект читался как незагрузившаяся картинка.
            Здесь стояли весы, но они же служат знаком в шапке и гравюрой
            Фемиды фоном: один мотив трижды читается не фирменным стилем, а
            нехваткой картинок. Стопка кодексов ту же мысль говорит иначе. */}
        <div className="mt-5 grid gap-8 lg:grid-cols-[minmax(0,8fr)_minmax(0,4fr)] lg:items-center">
          <div className="grid gap-x-10 gap-y-4 sm:grid-cols-2">
            {LEGAL.map((service) => (
              <div key={service.title} className="flex items-start gap-4">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-neutral-200 bg-neutral-100 text-accent-600">
                  <service.icon className="h-[18px] w-[18px]" aria-hidden="true" />
                </span>
                {/* Заголовок отдельной строкой, а не в подбор с описанием:
                    в подбор он терялся, и четыре пункта читались сплошным
                    текстом с тире посередине. */}
                <p className="min-w-0 text-sm">
                  <span className="block font-semibold text-neutral-950">{service.title}</span>
                  <span className="mt-0.5 block leading-relaxed text-neutral-600">
                    {service.text}
                  </span>
                </p>
              </div>
            ))}
          </div>
          <Figure
            {...IMAGES.lawbooks}
            frame={false}
            className="max-w-[170px] justify-self-center sm:max-w-[210px] lg:max-w-[240px]"
          />
        </div>
      </Reveal>
    </Section>
  )
}
