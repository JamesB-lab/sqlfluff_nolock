SELECT t2.col4
FROM (
    SELECT col1
    FROM table1
    WHERE col2 IS NOT NULL
) AS filtered_t1
LEFT JOIN table2 AS t2 ON t2.col3 = filtered_t1.col1
UNION
SELECT value
FROM SPLIT_STRINGS('a,b,c', ',')
