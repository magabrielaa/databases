-- Amongst users from the user table that have at least 200 reviews, find the 2 “most similar” users,
-- where the similarity of two users is defined as the number of shared businesses they’ve visited. 

-- Assume a user has visited a business if he or she has a review or a tip on a business. 
-- (given as user_id1, user_id2, similarity) Count business_ids even if there is no corresponding id 
-- in the business table. Do not double count pairs (eg James, Sinclair is the same as Sinclair, James). 
-- Do not double count visits (eg do not count user’s total reviewing and tipping of a location, rather 
-- count as a user visiting that location at least once).

WITH    sub_users AS (SELECT u.user_id FROM review r JOIN users u ON r.user_id = u.user_id 
                     GROUP BY u.user_id HAVING COUNT(r.review_id) >= 200),
        revs AS (SELECT DISTINCT user_id, business_id FROM review),
        tips AS (SELECT DISTINCT user_id, business_id FROM tip),
        complete AS (SELECT * FROM revs UNION SELECT * FROM tips)
SELECT DISTINCT c1.user_id AS user_id1, c2.user_id AS user_id2, COUNT(*) AS similarity 
FROM complete c1, complete c2
WHERE c1.business_id = c2.business_id 
AND c1.user_id < c2.user_id
AND c1.user_id IN (SELECT * FROM sub_users)
AND c2.user_id IN (SELECT * FROM sub_users)
GROUP BY c1.user_id, c2.user_id
ORDER BY similarity DESC
LIMIT 1;


