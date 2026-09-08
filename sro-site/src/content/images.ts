// Тематические изображения страницы (ЧАСТЬ 4 ТЗ). Держим их в одном месте:
// alt, размеры и пути нужны и в разметке, и в учёте лицензий
// (public/img/CREDITS.md), и расходиться они не должны.
//
// Все кадры — боевые, источники и лицензии подтверждены.
//
// Слот legal (весы) снят 04.09.2026 вместе с блоком «Смежные юридические
// задачи»: заказчик убрал блок, а кадр жил только в нём. Файлы лежат
// в assets-src/legal-spare.*, лицензия записана в CREDITS.md — вернуть
// можно одной строкой.
//
// Три кадра construction/design/survey — одна серия: они стоят рядом в секции
// «Виды СРО», по одному на вид, и потому приведены к общей плотности
// (средняя яркость 91-103) и к общей пропорции 16:9. Меняете один — приводите
// к серии и остальные, иначе карточки в ряду разъедутся по тону; рецепт с
// точными гаммами записан в public/img/CREDITS.md.
export type PageImage = {
  src: string
  // Необязателен: у векторной графики второго формата нет и не нужно.
  srcAvif?: string
  alt: string
  width: number
  height: number
  ratio: string
  fit?: 'cover' | 'contain'
}

export const IMAGES = {
  construction: {
    src: './img/construction.webp',
    srcAvif: './img/construction.avif',
    alt: 'Два башенных крана на фоне неба',
    width: 1000,
    height: 563,
    ratio: 'aspect-[16/9]',
  },
  design: {
    src: './img/design.webp',
    srcAvif: './img/design.avif',
    alt: 'Архивный чертёж: продольный разрез жилого дома',
    width: 1000,
    height: 563,
    ratio: 'aspect-[16/9]',
  },
  survey: {
    src: './img/survey.webp',
    srcAvif: './img/survey.avif',
    alt: 'Геодезический прибор на штативе на площадке инженерных изысканий',
    width: 1000,
    height: 562,
    ratio: 'aspect-[16/9]',
  },
  documents: {
    src: './img/documents.webp',
    srcAvif: './img/documents.avif',
    alt: 'Стопка папок с подшитыми документами крупным планом',
    width: 1200,
    height: 899,
    ratio: 'aspect-[4/3]',
  },
  // Первый экран — кадр заказчика (desk.*). Раньше этот же файл стоял фоном
  // под квизом, и заказчик справедливо заметил повтор: одна сцена открывала
  // и закрывала страницу. Под квизом теперь свой кадр (quiz-bg.*, см.
  // Quiz.tsx), а здесь кадр стола остался один.
  hero: {
    src: './img/desk.webp',
    srcAvif: './img/desk.avif',
    alt: 'Строительная каска, уровень и планы этажей на бетонном полу',
    width: 1600,
    height: 1068,
    ratio: 'aspect-[4/3]',
  },
} satisfies Record<string, PageImage>
