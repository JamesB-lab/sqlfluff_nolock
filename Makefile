.PHONY: install
install:
	pip install -e .

clear:
	clear

.PHONY: test
test: install clear
	pytest -s test/

rm_fixed:
	rm -rf examples/*.fixed.sql

.PHONY: lint
lint: install clear rm_fixed
	sqlfluff lint --dialect tsql .

.PHONY: fix
fix: install clear rm_fixed
	sqlfluff fix --dialect tsql --fixed-suffix .fixed  examples