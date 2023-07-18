-- Find the number of distinct business_ids that do not have any reviews. 
-- For this query, consider the full review table regardless of matching users 
-- (e.g consider reviews that do not have any matching user_id in the users table). 
--(given as count)

SELECT COUNT(b.business_id) 
FROM business AS b LEFT JOIN review as r ON b.business_id = r.business_id
WHERE review_id IS NULL;