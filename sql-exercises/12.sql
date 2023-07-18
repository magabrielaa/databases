SELECT category, AVG(avgscore) AS avg
FROM games
NATURAL JOIN gamecat 
NATURAL JOIN categories
GROUP BY category
ORDER BY avg DESC, category ASC
LIMIT 5;