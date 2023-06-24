SELECT mt.mycol
FROM mytable AS mt
LEFT JOIN othertable AS ot ON mt.id = ot.id
ORDER BY mt.mycol;
