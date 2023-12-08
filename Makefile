build:
	python -m build

install-build-deps:
	pip install build virtualenv twine

clean:
	rm -rf dist *.egg-info

upload:
	python -m twine upload dist/*
