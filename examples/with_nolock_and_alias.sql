SELECT mytable.mycol
FROM mytable AS mt WITH (NOLOCK)
LEFT JOIN othertable AS ot WITH (NOLOCK) ON mt.id = ot.id
ORDER BY mytable.mycol;
