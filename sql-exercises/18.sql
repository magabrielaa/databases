-- For the 10 users from the prior question, calculate the average 
--stars of all their reviews. Use a nested subquery to calculate the result. 
--(given as avg)

SELECT AVG(r.stars)
FROM users AS u INNER JOIN review AS r ON u.user_id = r.user_id
WHERE u.user_id IN
(SELECT user_id FROM(
SELECT u.user_id, COUNT(r.review_id) AS review_count 
FROM users AS u INNER JOIN review AS r ON u.user_id = r.user_id
GROUP BY (u.user_id) 
ORDER BY review_count DESC
LIMIT 10) AS temp);
