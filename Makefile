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
	docker pull kbase/runtester
	docker tag kbase/runtester test/runtester


test:
	nosetests -A "not online" -s -x -v --with-coverage --cover-package=JobRunner --cover-erase --cover-html --cover-html-dir=./test_coverage .


clean:
	rm -rfv $(LBIN_DIR)

