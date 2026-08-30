import { AboutExpert } from './components/AboutExpert'
import { Contacts } from './components/Contacts'
import { Documents } from './components/Documents'
import { FAQ } from './components/FAQ'
import { Footer } from './components/Footer'
import { Header } from './components/Header'
import { Hero } from './components/Hero'
import { LegalProvider } from './components/LegalDocs'
import { MobileBar } from './components/MobileBar'
import { Pricing } from './components/Pricing'
import { Problems } from './components/Problems'
import { Process } from './components/Process'
import { Quiz } from './components/Quiz'
import { QuizProvider } from './components/QuizContext'
import { Services } from './components/Services'
import { SroTypes } from './components/SroTypes'
import { Trust } from './components/Trust'
import { ThemisBackdrop } from './components/ui/ThemisBackdrop'

export default function App() {
  return (
    <QuizProvider>
      <LegalProvider>
        <div id="top" className="relative">
          {/* Фоновая гравюра лежит позади всего контента: сам контент едет
              выше по z, поэтому подложка не перехватывает ни клики, ни фокус. */}
          <ThemisBackdrop />
          <div className="relative z-10">
            <Header />
            <main>
              {/* Порядок секций: от «кто вы и с чем пришли» к заявке.
                  Квиз стоит в конце и работает закрывающим призывом —
                  его первый вопрос задаётся ещё на первом экране, в Hero. */}
              <Hero />
              <Trust />
              {/* Сразу под первым экраном — три вида СРО: посетитель должен
                  узнать свою область раньше, чем начнёт читать про услуги. */}
              <SroTypes />
              <Problems />
              <Services />
              <Process />
              <Documents />
              <Pricing />
              <AboutExpert />
              {/* Контакты в середине: убеждение уже сработало (человек узнал
                  про эксперта), а финалом страницы остаётся квиз — главная
                  точка конверсии и положена последней. */}
              <Contacts />
              <FAQ />
              <Quiz />
            </main>
            <Footer />
            {/* Отступ под фиксированную мобильную панель быстрых контактов (с учётом safe-area) */}
            <div
              className="md:hidden"
              style={{ height: 'calc(4rem + env(safe-area-inset-bottom))' }}
              aria-hidden="true"
            />
            <MobileBar />
          </div>
        </div>
      </LegalProvider>
    </QuizProvider>
  )
}
