import { AboutExpert } from './components/AboutExpert'
import { Contacts } from './components/Contacts'
import { Documents } from './components/Documents'
import { FAQ } from './components/FAQ'
import { Footer } from './components/Footer'
import { Header } from './components/Header'
import { Hero } from './components/Hero'
import { LegalProvider } from './components/LegalDocs'
import { LegalServices } from './components/LegalServices'
import { MobileBar } from './components/MobileBar'
import { Pricing } from './components/Pricing'
import { Problems } from './components/Problems'
import { Process } from './components/Process'
import { Quiz } from './components/Quiz'
import { QuizProvider } from './components/QuizContext'
import { Services } from './components/Services'
import { Trust } from './components/Trust'

export default function App() {
  return (
    <QuizProvider>
      <LegalProvider>
        <div id="top">
          <Header />
          <main>
            {/* Порядок секций: от «кто вы и с чем пришли» к заявке.
                Квиз стоит в конце и работает закрывающим призывом —
                его первый вопрос задаётся ещё на первом экране, в Hero. */}
            <Hero />
            <Trust />
            <Problems />
            <Services />
            <LegalServices />
            <Process />
            <Documents />
            <Pricing />
            <AboutExpert />
            <FAQ />
            <Quiz />
            <Contacts />
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
      </LegalProvider>
    </QuizProvider>
  )
}
