.PHONY: install
install:
	pip install -e .

.PHONY: lint
lint:
	sqlfluff lint --dialect tsql .

.PHONY: fix
fix:
	sqlfluff fix --dialect tsql .