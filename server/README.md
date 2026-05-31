

UPDATE ads SET country = 'russia' WHERE country = 'Россия';
UPDATE ads SET country = 'belarus' WHERE country = 'Беларусь';
UPDATE ads SET country = 'cyprus' WHERE country = 'Кипр';
UPDATE ads SET country = 'singapore' WHERE country = 'Singapore';


UPDATE ads SET ad_type = 'sale' WHERE ad_type='Продажа';
UPDATE ads SET ad_type = 'rent' WHERE ad_type='Аренда';

UPDATE ads SET condition = 'unknown' WHERE condition='Не указано';