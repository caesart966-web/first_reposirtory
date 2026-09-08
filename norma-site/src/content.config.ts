import { defineCollection, z } from 'astro:content'
import { glob } from 'astro/loaders'

// База знаний. Каждая статья — обычный текстовый файл в src/content/articles/.
// Имя файла становится адресом статьи: subpodryad.md → /baza-znaniy/subpodryad/
const articles = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/articles' }),
  schema: z.object({
    title: z.string(),
    // Заголовок и описание для поисковика. Если не заданы — берутся из title.
    metaTitle: z.string().optional(),
    description: z.string(),
    // Даты обязательны: в нише, где всё устаревает, статья без даты бесполезна.
    published: z.coerce.date(),
    updated: z.coerce.date().optional(),
    // Короткое описание для карточки в списке статей.
    excerpt: z.string(),
    // Ссылка на страницу услуги: статья обязана вести дальше, а не в тупик.
    relatedService: z.object({ label: z.string(), url: z.string() }).optional(),
    // Раздел списка. Двадцать четыре статьи сплошным списком не читаются:
    // глаз не находит, где кончается одна тема и начинается другая.
    group: z.enum(['need', 'money', 'membership', 'check']).default('need'),
    // Место внутри раздела: чем меньше, тем выше. Сортировать список
    // по дате нельзя — статьи, написанные в один день, встают как попало,
    // а самые нужные уезжают вниз просто потому, что написаны раньше.
    order: z.number().default(0),
  }),
})

export const collections = { articles }
