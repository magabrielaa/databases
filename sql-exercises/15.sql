SELECT DISTINCT designer, category, maxplaytime AS max FROM
(SELECT designer, category, maxplaytime,
RANK()
OVER(PARTITION BY category ORDER BY maxplaytime DESC)
AS my_place
FROM games
NATURAL JOIN gamecat 
NATURAL JOIN categories
NATURAL JOIN desgame
NATURAL JOIN designers
WHERE designer IS NOT NULL) AS temp
WHERE my_place = 1
ORDER BY category DESC, designer ASC;