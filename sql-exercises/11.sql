SELECT category, COUNT(name) AS cnt
FROM games
NATURAL JOIN gamecat 
NATURAL JOIN categories
WHERE numvotes > 200
GROUP BY (category)
HAVING COUNT(name) >= 15;

