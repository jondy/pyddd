.PHONY: all

all: test/pyddd-ipa.dll test/test-ipa.exe

PYTHONINC := /cygdrive/c/Python27/Include
PYTHONLIB := -L/cygdrive/d/projects/platforms/windows/python27 -lpython27
CFLAGS := -g -I$(PYTHONINC)
CC := i686-pc-mingw32-gcc

test/pyddd-ipa.dll: ipa.c
	$(CC) -shared $(CFLAGS) $< -Wl,-lpthread -o $@

test/test-ipa.exe: test/test-ipa.c ipa.c
	$(CC) -mconsole -o $@ $(CFLAGS) -DTEST_IPA $< ipa.c $(PYTHONLIB) -Wl,-lpthread

test: test/test-ipa.exe
	test/test-ipa.exe
