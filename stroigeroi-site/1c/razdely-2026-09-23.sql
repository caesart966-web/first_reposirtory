-- =====================================================================
--  Разделы каталога после загрузки из 1С (23.09.2026)
--  Запускается один раз, во вкладке SQL phpMyAdmin, целиком.
-- =====================================================================
--  1. Скрывает мусорные разделы прежнего каталога: «Склад» (71),
--     «Товар» (78), «А1 САНТЕХНИКА» (79) и всё, что внутри них. Ещё в макете
--     они были помечены как «покупателю ничего не говорят». Берутся только
--     из oc_old_categories — списка разделов, где не осталось ни одного
--     видимого товара, — так что ветку с товарами это не заденет.
--
--  2. Кладёт 14 разделов из выгрузки 1С внутрь отделов магазина, чтобы
--     в меню остались 15 отделов, а не 29 пунктов вперемешку:
--       59 «Инструменты» — всё, что работает руками и от розетки;
--       73 «Строительное оборудование» — бетономешалки, генераторы,
--          пылесосы и мойки;
--       65 «Крепёж и фурнитура» — расходники и крепёж.
--     Путь раздела (oc_category_path) движок сам не пересобирает,
--     поэтому он пересобирается здесь: путь родителя плюс свой уровень.
--     Раздел переносится только если он сейчас на верхнем уровне и у нового
--     родителя есть путь. Иначе он остаётся на месте, а в отчёте
--     внизу видно, что не перенесено.
--
--  Защита от повторного запуска: обе таблицы создаются без IF NOT EXISTS.
--  Второй запуск остановится на первой же строке и ничего не испортит.
--
--  Вернуть скрытые разделы:
--    UPDATE `oc_category` c JOIN `oc_hidden_categories` h
--      ON h.`category_id` = c.`category_id` SET c.`status` = h.`old_status`;
--  Где раздел был до переноса — в oc_moved_categories (old_parent, old_top).
-- =====================================================================

SET @lang := (SELECT l.`language_id` FROM `oc_language` l
              JOIN `oc_setting` s ON s.`value` = l.`code`
               AND s.`key` = 'config_language' AND s.`store_id` = 0 LIMIT 1);

CREATE TABLE `oc_hidden_categories` AS
SELECT o.`category_id`, o.`old_status`
FROM `oc_old_categories` o
WHERE o.`category_id` IN (71, 78, 79)
   OR o.`category_id` IN (SELECT cp.`category_id` FROM `oc_category_path` cp
                           WHERE cp.`path_id` IN (71, 78, 79));

UPDATE `oc_category` c
JOIN `oc_hidden_categories` h ON h.`category_id` = c.`category_id`
SET c.`status` = 0;

CREATE TABLE `oc_moved_categories` (
  `cat_guid`    CHAR(36) NOT NULL,
  `new_parent`  INT NOT NULL,
  `category_id` INT DEFAULT NULL,
  `old_parent`  INT DEFAULT NULL,
  `old_top`     TINYINT DEFAULT NULL,
  `lvl`         INT DEFAULT NULL,
  PRIMARY KEY (`cat_guid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci;

INSERT INTO `oc_moved_categories` (`cat_guid`, `new_parent`) VALUES
('5240cfc2-c0a1-11ee-b034-a8a1590a763d', 59),
('f6b849f3-f38f-11e8-bf10-00241dd74de5', 59),
('0a3526a0-9f44-11f0-b050-a8a1590a763d', 59),
('9a13e17c-fdb8-11e3-bfb6-00006c188258', 59),
('262f1f71-8867-11ec-80f3-9c5c8e769bd3', 59),
('e6ec88c6-ee75-11ef-b04d-a8a1590a763d', 59),
('38be2943-34ae-11e9-80cd-9c5c8e769bd3', 59),
('8a8d9432-f41b-11e8-bf55-00241dd74de5', 59),
('2f009eb0-35e7-11ec-80f3-9c5c8e769bd3', 59),
('303caa66-f0f7-11e8-9df8-00241dd74de5', 73),
('52c2c598-6d51-11ea-4694-f0795970f84c', 73),
('86e06be6-9f43-11f0-b050-a8a1590a763d', 73),
('0d8873c3-7046-11e4-bf71-50465d5010be', 73),
('892c22c8-2479-11e7-ab49-50465d5010be', 65);

UPDATE `oc_moved_categories` m
JOIN (SELECT DISTINCT `cat_guid`, `category_id` FROM `oc_import_1c`
      WHERE `category_id` IS NOT NULL) i
  ON CAST(i.`cat_guid` AS BINARY) = CAST(m.`cat_guid` AS BINARY)
JOIN `oc_category` c ON c.`category_id` = i.`category_id`
SET m.`category_id` = c.`category_id`,
    m.`old_parent`  = c.`parent_id`,
    m.`old_top`     = c.`top`,
    m.`lvl` = (SELECT MAX(pp.`level`) + 1 FROM `oc_category_path` pp
               WHERE pp.`category_id` = m.`new_parent`);

UPDATE `oc_category` c
JOIN `oc_moved_categories` m ON m.`category_id` = c.`category_id`
SET c.`parent_id` = m.`new_parent`, c.`top` = 0
WHERE m.`old_parent` = 0 AND m.`lvl` IS NOT NULL;

DELETE cp FROM `oc_category_path` cp
JOIN `oc_moved_categories` m ON m.`category_id` = cp.`category_id`
WHERE m.`old_parent` = 0 AND m.`lvl` IS NOT NULL;

INSERT INTO `oc_category_path` (`category_id`, `path_id`, `level`)
SELECT m.`category_id`, pp.`path_id`, pp.`level`
FROM `oc_moved_categories` m
JOIN `oc_category_path` pp ON pp.`category_id` = m.`new_parent`
WHERE m.`old_parent` = 0 AND m.`lvl` IS NOT NULL;

INSERT INTO `oc_category_path` (`category_id`, `path_id`, `level`)
SELECT m.`category_id`, m.`category_id`, m.`lvl`
FROM `oc_moved_categories` m
WHERE m.`old_parent` = 0 AND m.`lvl` IS NOT NULL;

SELECT cd.`name` AS `раздел из 1С`,
       IFNULL(pd.`name`, '— остался наверху') AS `теперь внутри`,
       (SELECT COUNT(*) FROM `oc_category_path` cp
         WHERE cp.`category_id` = m.`category_id`) AS `строк пути`
FROM `oc_moved_categories` m
LEFT JOIN `oc_category` c ON c.`category_id` = m.`category_id`
LEFT JOIN `oc_category_description` cd
  ON cd.`category_id` = m.`category_id` AND cd.`language_id` = @lang
LEFT JOIN `oc_category_description` pd
  ON pd.`category_id` = c.`parent_id` AND pd.`language_id` = @lang
ORDER BY c.`parent_id`, cd.`name`;

SELECT cd.`name` AS `скрыт как мусор`
FROM `oc_hidden_categories` h
LEFT JOIN `oc_category_description` cd
  ON cd.`category_id` = h.`category_id` AND cd.`language_id` = @lang
ORDER BY cd.`name`;
