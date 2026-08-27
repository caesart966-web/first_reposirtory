// Четыре тематических изображения страницы (ЧАСТЬ 4 ТЗ). Держим их в одном
// месте: alt, размеры и пути нужны и в разметке, и в учёте лицензий
// (public/img/CREDITS.md), и расходиться они не должны.
//
// ВНИМАНИЕ: construction и survey — боевые кадры, источники и лицензии
// подтверждены (см. public/img/CREDITS.md). design и legal пока подписанные
// заглушки из scripts/make-image-placeholders.py: их источники известны, но
// скачать файлы из этого окружения нельзя — политика egress блокирует
// unsplash.com и rawpixel.com. Боевые кадры обрабатываются
// scripts/prepare-photo.py и кладутся под теми же именами; менять разметку
// при замене не нужно, кроме width/height, если пропорция другая.
export type PageImage = {
  src: string
  srcAvif: string
  alt: string
  width: number
  height: number
  ratio: string
  fit?: 'cover' | 'contain'
}

export const IMAGES = {
  design: {
    src: './img/design.webp',
    srcAvif: './img/design.avif',
    alt: 'Архивная синька: продольный разрез жилого дома с лестничными маршами и перекрытиями',
    width: 1200,
    height: 900,
    ratio: 'aspect-[4/3]',
  },
  construction: {
    src: './img/construction.webp',
    srcAvif: './img/construction.avif',
    alt: 'Стопка папок с подшитыми документами крупным планом',
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
    alt: 'Штриховой рисунок: равновесные аптекарские весы с двумя чашами',
    // Размеры родные, а не 1200×800 из ТЗ: это вырезанный объект, а не
    // фотография — подгонять его под прямоугольник нечем, обрезка отрубила бы
    // чаши и основание. Рамки у него нет, поэтому и пропорция бокса — родная:
    // навязанный 4:3 оставлял бы пустые поля по бокам от весов.
    width: 1200,
    height: 1238,
    ratio: 'aspect-[1200/1238]',
    fit: 'contain',
  },
} satisfies Record<string, PageImage>
