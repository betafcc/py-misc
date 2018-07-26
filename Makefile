SRC := misc
JUPYTER_ROOT := notebooks


init:
	pipenv install --skip-lock
	pipenv install --dev --skip-lock

	pipenv run jupyter nbextension enable --py widgetsnbextension --sys-prefix
	pipenv run jupyter labextension install @jupyter-widgets/jupyterlab-manager


notebook:
	cd $(JUPYTER_ROOT) && pipenv run jupyter notebook


lab:
	cd $(JUPYTER_ROOT) && pipenv run jupyter lab


validate:
	make lint && make typecheck


lint:
	pipenv run flake8


typecheck:
	pipenv run mypy --ignore-missing-imports $(SRC)
