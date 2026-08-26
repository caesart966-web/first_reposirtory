import { AboutExpert } from './components/AboutExpert'
import { Contacts } from './components/Contacts'
import { Documents } from './components/Documents'
import { FAQ } from './components/FAQ'
import { FinalCTA } from './components/FinalCTA'
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
import { Services } from './components/Services'
import { Trust } from './components/Trust'

export default function App() {
  return (
    <LegalProvider>
      <div id="top">
        <Header />
        <main>
          <Hero />
          <Services />
          <LegalServices />
          <Problems />
          <Process />
          <AboutExpert />
          <Pricing />
          <Quiz />
          <Documents />
          <Trust />
          <FAQ />
          <FinalCTA />
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
  )
}
