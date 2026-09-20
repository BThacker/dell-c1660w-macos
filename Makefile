SHELL := /bin/sh
CC := xcrun clang
CFLAGS := -std=c11 -O2 -Wall -Wextra -Werror -arch arm64 -mmacosx-version-min=13.0
LDLIBS := -lcups
FILTER := build/rastertohbpl1

.PHONY: all test test-pages sanitize stage install uninstall release package-test clean
all: $(FILTER)

build:
	mkdir -p build

build/version.h: VERSION scripts/version_header.py | build
	python3 scripts/version_header.py

$(FILTER): src/rastertohbpl1.c src/hbpl1.c src/hbpl1.h build/version.h | build
	$(CC) $(CFLAGS) -Isrc -Ibuild src/rastertohbpl1.c src/hbpl1.c $(LDLIBS) -o $@
	codesign --force --sign - $@

build/raster-fixture: tests/raster_fixture.c | build
	$(CC) $(CFLAGS) $< $(LDLIBS) -o $@

build/decode-hbpl1: tests/decode_hbpl1.c | build
	$(CC) $(CFLAGS) $< -o $@

build/pdf-fixture: tests/pdf_fixture.swift | build
	xcrun swiftc -module-cache-path build/swift-cache $< -o $@

test: all build/raster-fixture build/decode-hbpl1 build/pdf-fixture
	python3 tests/test_driver.py

test-pages: build/pdf-fixture
	build/pdf-fixture build/test-page.pdf
	build/pdf-fixture build/landscape-test-page.pdf landscape

sanitize: build/version.h | build
	$(CC) $(CFLAGS) -O1 -g -fsanitize=address,undefined -fno-sanitize-recover=all -Isrc -Ibuild src/rastertohbpl1.c src/hbpl1.c $(LDLIBS) -o build/rastertohbpl1-sanitize
	$(MAKE) all build/raster-fixture build/decode-hbpl1
	HBPL_FILTER=build/rastertohbpl1-sanitize python3 tests/test_driver.py --synthetic

stage: all
	./scripts/install.sh --stage "$(CURDIR)/build/stage"

install: all
	./scripts/install.sh

uninstall:
	./scripts/uninstall.sh

release:
	python3 scripts/release.py

package-test:
	python3 tests/test_packaging.py

clean:
	rm -rf build
