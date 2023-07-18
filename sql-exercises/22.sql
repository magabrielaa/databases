-- Out of the users in the user table who have more than 50 reviews, find the user id whose
-- reviews have the lowest average star rating (there may be 1 or more users with the same 
-- lowest average star rating); 
-- for this user(s), find the names and ids of the businesses they gave the highest star ratings to
--  (again, there may be more than 1 such business). 
-- Your final output should be given as (user_id, user_name, business_id, business_name).
-- Use an outer join to account for business_ids that do not match records in the business table

WITH sub_users AS (SELECT user_id FROM review JOIN users USING(user_id)
                    GROUP BY user_id HAVING COUNT(review_id) > 50), -- users with over 50 reviews 
    avg_r (user1, avg_rate) AS (SELECT user_id, AVG(stars) FROM review JOIN users 
                                 USING(user_id) WHERE user_id IN (SELECT * FROM sub_users)
                                 GROUP BY user_id ORDER BY AVG(stars)), -- average rate per user
    lowest (min_rate) AS (SELECT MIN(avg_rate)FROM avg_r), -- min avg rate across all users 
    find_user AS (SELECT user1 FROM avg_r, lowest WHERE avg_r.avg_rate = lowest.min_rate) -- single user with min rate
SELECT user_id,
    users.name AS user_name,
    business_id,
    business.name AS business_name
FROM review
    INNER JOIN users USING(user_id)
    LEFT JOIN business USING(business_id)
WHERE user_id = (SELECT * FROM find_user)
ORDER BY review.stars DESC
LIMIT 1;