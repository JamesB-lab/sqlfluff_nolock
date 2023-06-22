SELECT mytable.mycol
FROM mytable
LEFT JOIN othertable ON mytable.id = othertable.id
ORDER BY mytable.mycol;
