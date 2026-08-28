// Тематические изображения страницы (ЧАСТЬ 4 ТЗ). Держим их в одном месте:
// alt, размеры и пути нужны и в разметке, и в учёте лицензий
// (public/img/CREDITS.md), и расходиться они не должны.
//
// Все кадры — боевые, источники и лицензии подтверждены. Слот проектирования
// (архивная синька) снят: секция «Документы» про пакет бумаг, а не про разрез
// здания, и кадр туда не попадал по смыслу. Файлы лежат в assets-src/
// (blueprint-spare.webp и исходник blueprint-crop-spare.jpg) — в сборку они
// не идут, но остаются под рукой.
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
  documents: {
    src: './img/documents.webp',
    srcAvif: './img/documents.avif',
    alt: 'Стопка папок с подшитыми документами крупным планом',
    width: 1200,
    height: 899,
    ratio: 'aspect-[4/3]',
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
