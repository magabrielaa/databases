SELECT AVG(avgscore), maxplayers FROM games GROUP BY (maxplayers) HAVING AVG(avgscore) > 6 ORDER BY (maxplayers);