import { AboutExpert } from './components/AboutExpert'
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
      <main>
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
        {/* Тёмный раздел с Фемидой — середина страницы, пауза между
            светлыми блоками. */}
        <Process />
        <Documents />
        <Specialists />
        <Pricing />
        {/* Лицензии, обучение сотрудников, ISO 9001 (02.10.2026) — после
            всего, что сказано про СРО, и перед «О компании». */}
        <Licenses />
        <AboutExpert />
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
