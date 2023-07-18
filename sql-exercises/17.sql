-- Find the 10 users with the most reviews. Only consider reviews that have a 
-- corresponding user tuple. In case of ties, break with name ascending (e.g. bob before sarah). 
--(given as user_id, name, review_count)

SELECT u.user_id, u.name, COUNT(r.review_id) AS review_count 
FROM users AS u INNER JOIN review AS r ON u.user_id = r.user_id
GROUP BY (u.user_id) 
ORDER BY review_count DESC, name
LIMIT 10;
