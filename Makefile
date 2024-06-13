build:
	python -m build

install-dev:
	python -m pip install -e '.[dev]'

clean:
	rm -rf build dist *.egg-info

upload:
	python -m twine upload dist/*

test:
	python -m groktest .
