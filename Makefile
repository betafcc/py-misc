SRC := misc
JUPYTER_ROOT := notebooks

init:
	poetry install

	poetry run jupyter nbextension enable --py widgetsnbextension --sys-prefix
	poetry run jupyter labextension install @jupyter-widgets/jupyterlab-manager


notebook:
	cd $(JUPYTER_ROOT) && poetry run jupyter notebook


lab:
	cd $(JUPYTER_ROOT) && poetry run jupyter lab


validate:
	make lint && make typecheck


lint:
	poetry run flake8


typecheck:
	poetry run mypy --ignore-missing-imports $(SRC)
