SELECT AVG(avgscore), maxplayers FROM games WHERE  maxplaytime < 100 GROUP BY (maxplayers) ORDER BY (maxplayers);