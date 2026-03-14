.PHONY: test serve

test:
	python3 -m unittest discover -s tests -v

serve:
	python3 -m http.server 8888
