SELECT designer, avgscore, name FROM
(SELECT designer, avgscore, name,
RANK()
OVER(PARTITION BY designer ORDER BY avgscore DESC)
AS my_place
FROM designers
NATURAL JOIN desgame
NATURAL JOIN games
WHERE numvotes >= 1000) AS temp
WHERE my_place = 1
ORDER BY avgscore DESC, designer ASC;