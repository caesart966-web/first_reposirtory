import { ARTICLES_SORTED } from '../content/articles'
import { IMAGES } from '../content/images'
import { home } from '../lib/site'
import { ArticleRows } from './Articles'
import { Contact } from './Contact'
import { Footer } from './Footer'
import { Header } from './Header'
import { MobileBar } from './MobileBar'
import { PageHero } from './PageHero'
import { Part } from './PageParts'

// Страница «Статьи» (/stati/, 15.10.2026): шапка с кадром, как у страниц
// услуг (книги с Градостроительным кодексом на столе), и все статьи
// строками, свежие сверху. Рубрик пока нет: при трёх-десяти статьях они
// делили бы список на группы по одной.
export const ARTICLES_TITLE = 'Статьи'

export function ArticlesIndex() {
  return (
    <div id="top">
      <Header />
      <main>
        <PageHero
          backHref={home()}
          backLabel="На главную"
          title={ARTICLES_TITLE}
          lead="Вопросы о вступлении в СРО, разобранные по закону: кому нужно членство, как выбрать организацию, что проверить до оплаты. У каждого утверждения — статья закона."
          image={IMAGES.svcPodbor}
        />
        <Part>
          <ArticleRows articles={ARTICLES_SORTED} />
        </Part>
        <Contact />
      </main>
      <Footer />
      <MobileBar />
    </div>
  )
}
