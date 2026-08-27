// Четыре тематических изображения страницы (ЧАСТЬ 4 ТЗ). Держим их в одном
// месте: alt, размеры и пути нужны и в разметке, и в учёте лицензий
// (public/img/CREDITS.md), и расходиться они не должны.
//
// ВНИМАНИЕ: construction и survey — боевые кадры, design и legal пока
// подписанные заглушки из scripts/make-image-placeholders.py. Боевые кадры
// обрабатываются scripts/prepare-photo.py и кладутся под теми же именами;
// менять разметку при замене не нужно, кроме width/height, если пропорция
// другая. Источник и лицензия установленных кадров ещё не подтверждены —
// см. public/img/CREDITS.md, до этого сайт публиковать нельзя.
export type PageImage = {
  src: string
  srcAvif: string
  alt: string
  width: number
  height: number
  ratio: string
}

export const IMAGES = {
  design: {
    src: './img/design.webp',
    srcAvif: './img/design.avif',
    alt: 'Архивный чертёж: план и разрез здания со штампом основной надписи',
    width: 1200,
    height: 900,
    ratio: 'aspect-[4/3]',
  },
  construction: {
    src: './img/construction.webp',
    srcAvif: './img/construction.avif',
    alt: 'Два башенных крана на фоне чистого неба',
    width: 2000,
    height: 700,
    ratio: 'aspect-[20/7]',
  },
  survey: {
    src: './img/survey.webp',
    srcAvif: './img/survey.avif',
    alt: 'Тахеометр на штативе на площадке инженерных изысканий',
    width: 1200,
    height: 900,
    ratio: 'aspect-[4/3]',
  },
  legal: {
    src: './img/legal.webp',
    srcAvif: './img/legal.avif',
    alt: 'Гравюра: аптекарские весы, печать и документ',
    width: 1200,
    height: 800,
    ratio: 'aspect-[3/2]',
  },
} satisfies Record<string, PageImage>
