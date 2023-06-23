.PHONY: install
install:
	pip install -e .

clear:
	clear

.PHONY: test
test: install clear
	pytest test/

.PHONY: lint
lint: install clear
	sqlfluff lint --dialect tsql .

.PHONY: fix
fix: install clear
	sqlfluff fix --dialect tsql -vvvv .