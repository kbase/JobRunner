.PHONY: test

docker:
	docker build -t kbase/indexrunner .

runtester: test/runtester.ready

test/runtester.ready:
	(cd test && git clone https://github.com/kbaseapps/RunTester && cd RunTester && docker build -t test/runtester .)
	touch runtester.ready

mock:
	docker build -t mock_app ./test/mock_app

testimage:
	docker pull docker.io/kbase/runtester
	docker tag docker.io/kbase/runtester test/runtester

updatereqs:
	uv pip compile --all-extras --output-file requirements.txt pyproject.toml

test:
	PYTHONPATH=. uv run pytest -m "not online" test

clean:
	rm -rfv $(LBIN_DIR)

