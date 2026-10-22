import { AboutExpert } from './components/AboutExpert'
import { LatestArticles } from './components/Articles'
import { Contact } from './components/Contact'
import { Documents } from './components/Documents'
import { FAQ } from './components/FAQ'
import { Footer } from './components/Footer'
import { Header } from './components/Header'
import { Hero } from './components/Hero'
import { Licenses } from './components/Licenses'
import { MobileBar } from './components/MobileBar'
import { Pricing } from './components/Pricing'
import { Process } from './components/Process'
import { Regions } from './components/Regions'
import { Services } from './components/Services'
import { Specialists } from './components/Specialists'
import { Trust } from './components/Trust'
import { useHashScroll } from './lib/useHashScroll'

export default function App() {
  // Якорь в адресе должен сработать после того, как разметка отрисована.
  useHashScroll()

  return (
    <div id="top">
      <Header />
      <main id="main" className="focus:outline-none">
        {/* Порядок с 24.09.2026. Первый экран (с 26.09.2026 — «лист и окно»)
            сам показывает три вида СРО списком, поэтому сетки карточек видов
            под ним нет. Дальше —
            от услуг к «как работаю» и «сколько стоит». Квиза
            больше нет: сайт рекламный, заявки — звонком и в мессенджерах,
            и страница заканчивается разделом «Связаться». */}
        <Hero />
        <Trust />
        {/* «С чем обращаются» (три типовые ситуации) снят 01.10.2026:
            документы и специалисты НРС — те же темы, что карточки услуг,
            разделы «Документы» и «Специалисты НРС» ниже и вопрос в FAQ.
            Главная говорила о них по три-четыре раза. */}
        <Services />
        {/* Порядок с 22.10.2026 (разбор главной): сначала то, что решает,
            писать ли вообще, — что делаю, как идёт работа и как считается
            цена; затем частности — специалисты НРС и документы; затем
            «О компании», статьи и вопросы. На телефоне «Форматы работы»
            стоят после 5 экранов прокрутки вместо 8, «О компании» — после
            10 вместо 12. «Специалисты НРС» — до «Документов»: без двух
            специалистов в СРО не примут, и от этого зависит, можно ли
            вступать вообще.
            Светлые и тёмные разделы чередуются, как прежде: фон у каждого
            раздела свой, и соседи с одинаковым фоном слились бы в один. */}
        <Process />
        <Pricing />
        <Specialists />
        <Documents />
        {/* Лицензии, обучение сотрудников, ISO 9001 (02.10.2026) — после
            всего, что сказано про СРО, и перед «О компании». До 1024 px
            листы свёрнуты в строки (22.10.2026). */}
        <Licenses />
        <AboutExpert />
        {/* Три свежие статьи (15.10.2026): после тёмного «О компании»
            на кремовом фоне, перед светлыми «Вопросами» — короткие ответы
            и подробные разборы стоят рядом. */}
        <LatestArticles />
        <FAQ />
        <Regions />
        <Contact />
      </main>
      <Footer />
      {/* Отступа под нижней панелью связи нет (30.09.2026): панель уходит,
          как только на экран въезжает «Связаться», и под подвалом отступ
          оставлял светлую полосу на телефоне. */}
      <MobileBar />
    </div>
  )
}
