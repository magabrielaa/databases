-- Amongst users from the user table that have at least 200 reviews, find the 2 “most similar” 
-- users, where the similarity of two users is defined as the number of shared businesses they’ve
-- reviewed. (given as user_id1, user_id2, similarity)
-- Count reviews even if the business_ids has no corresponding id in the business table. 
-- Do not double count pairs (eg James, Sinclair is the same as Sinclair, James).

WITH temp AS (SELECT u.user_id FROM review r JOIN users u ON r.user_id = u.user_id 
            GROUP BY u.user_id HAVING COUNT(r.review_id) >= 200)
SELECT DISTINCT r1.user_id AS user_id1, r2.user_id AS user_id2, COUNT(*) AS similarity 
FROM review r1, review r2
WHERE r1.business_id = r2.business_id 
AND r1.user_id < r2.user_id
AND r1.user_id IN (SELECT * FROM temp)
AND r2.user_id IN (SELECT * FROM temp)
GROUP BY r1.user_id, r2.user_id
ORDER BY similarity DESC
LIMIT 1;