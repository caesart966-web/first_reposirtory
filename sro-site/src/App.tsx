import { AboutExpert } from './components/AboutExpert'
import { Contact } from './components/Contact'
import { Documents } from './components/Documents'
import { FAQ } from './components/FAQ'
import { Footer } from './components/Footer'
import { Header } from './components/Header'
import { Hero } from './components/Hero'
import { MobileBar } from './components/MobileBar'
import { Pricing } from './components/Pricing'
import { Problems } from './components/Problems'
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
        {/* Порядок с 24.09.2026. Первый экран — слайдер трёх видов СРО: он
            заменил и прежний герой, и сетку карточек видов под ним. Дальше —
            от «с чем приходят» к «как работаю» и «сколько стоит». Квиза
            больше нет: сайт рекламный, заявки — звонком и в мессенджерах,
            и страница заканчивается разделом «Связаться». */}
        <Hero />
        <Trust />
        <Problems />
        <Services />
        {/* Тёмный раздел с Фемидой — середина страницы, пауза между
            светлыми блоками. */}
        <Process />
        <Documents />
        <Specialists />
        <Pricing />
        <AboutExpert />
        <FAQ />
        <Regions />
        <Contact />
      </main>
      <Footer />
      {/* Отступ под фиксированную мобильную панель быстрых контактов */}
      <div
        className="md:hidden"
        style={{ height: 'calc(4rem + env(safe-area-inset-bottom))' }}
        aria-hidden="true"
      />
      <MobileBar />
    </div>
  )
}
