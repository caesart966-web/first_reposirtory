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
    order: z.number().default(0),
  }),
})

export const collections = { articles }
