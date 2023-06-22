SELECT mytable.mycol
FROM mytable WITH (NOLOCK)
LEFT JOIN othertable WITH (NOLOCK) ON mytable.id = othertable.id
ORDER BY mytable.mycol;
