build:
	python -m build

clean:
	rm -rf dist
	rm -rf *.egg-info

upload:
	python -m twine upload dist/*
