# GNU Make; execute on Linux after loading <COMPILER_MODULE>.
SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
.NOTPARALLEL:
.DEFAULT_GOAL := all

PREFIX ?= $(HOME)/local/udales-intel
ARCHIVES ?= $(HOME)/udales-deps-src
WORK ?= $(HOME)/udales-deps-build
JOBS ?= 4
CC := icc
FC := ifort
F77 := ifort
export CC FC F77
# Do not apply the solver's real-kind flags to dependency libraries.
export CFLAGS := -O2
export FCFLAGS := -O2
export FFLAGS := -O2
export PATH := $(PREFIX)/bin:$(PATH)
export LD_LIBRARY_PATH := $(PREFIX)/lib:$(LD_LIBRARY_PATH)

STAMP := $(WORK)/stamps
LOG := $(WORK)/logs

.PHONY: all preflight zlib hdf5 netcdf-c netcdf-fortran verify help
all: netcdf-fortran verify
zlib: $(STAMP)/zlib
hdf5: $(STAMP)/hdf5
netcdf-c: $(STAMP)/netcdf-c
netcdf-fortran: $(STAMP)/netcdf-fortran

preflight:
	@command -v $(CC) >/dev/null
	@command -v $(FC) >/dev/null
	@command -v tar >/dev/null
	@command -v sha256sum >/dev/null
	@test "$(JOBS)" -gt 0
	@cd "$(ARCHIVES)" && sha256sum -c SHA256SUMS
	@mkdir -p "$(PREFIX)" "$(WORK)" "$(STAMP)" "$(LOG)"

$(STAMP)/zlib: $(ARCHIVES)/zlib-1.3.1.tar.gz | preflight
	@echo 'Building zlib; log: $(LOG)/zlib.log'
	@{ tar -xzf "$<" -C "$(WORK)"; cd "$(WORK)/zlib-1.3.1"; ./configure --prefix="$(PREFIX)"; $(MAKE) -j$(JOBS); $(MAKE) check; $(MAKE) install; } >"$(LOG)/zlib.log" 2>&1
	@touch "$@"

$(STAMP)/hdf5: $(ARCHIVES)/hdf5-1.12.2.tar.gz $(STAMP)/zlib | preflight
	@echo 'Building HDF5; log: $(LOG)/hdf5.log'
	@{ tar -xzf "$<" -C "$(WORK)"; cd "$(WORK)/hdf5-1.12.2"; ./configure --prefix="$(PREFIX)" --libdir="$(PREFIX)/lib" --with-zlib="$(PREFIX)" --enable-shared --disable-fortran --disable-cxx; $(MAKE) -j$(JOBS); $(MAKE) check; $(MAKE) install; } >"$(LOG)/hdf5.log" 2>&1
	@touch "$@"

$(STAMP)/netcdf-c: $(ARCHIVES)/netcdf-c-4.9.2.tar.gz $(STAMP)/hdf5 | preflight
	@echo 'Building NetCDF C; log: $(LOG)/netcdf-c.log'
	@{ tar -xzf "$<" -C "$(WORK)"; cd "$(WORK)/netcdf-c-4.9.2"; CPPFLAGS="-I$(PREFIX)/include" LDFLAGS="-L$(PREFIX)/lib -Wl,-rpath,$(PREFIX)/lib" ./configure --prefix="$(PREFIX)" --libdir="$(PREFIX)/lib" --enable-netcdf-4 --enable-shared --disable-dap --disable-nczarr --disable-libxml2; $(MAKE) -j$(JOBS); $(MAKE) check; $(MAKE) install; } >"$(LOG)/netcdf-c.log" 2>&1
	@touch "$@"

$(STAMP)/netcdf-fortran: $(ARCHIVES)/netcdf-fortran-4.6.1.tar.gz $(STAMP)/netcdf-c | preflight
	@echo 'Building NetCDF Fortran; log: $(LOG)/netcdf-fortran.log'
	@{ tar -xzf "$<" -C "$(WORK)"; cd "$(WORK)/netcdf-fortran-4.6.1"; CPPFLAGS="-I$(PREFIX)/include" LDFLAGS="-L$(PREFIX)/lib -Wl,-rpath,$(PREFIX)/lib" ./configure --prefix="$(PREFIX)" --libdir="$(PREFIX)/lib" --enable-shared; $(MAKE) -j$(JOBS); $(MAKE) check; $(MAKE) install; } >"$(LOG)/netcdf-fortran.log" 2>&1
	@touch "$@"

verify: $(STAMP)/netcdf-fortran
	@"$(PREFIX)/bin/nc-config" --all
	@"$(PREFIX)/bin/nf-config" --all
	@test "$$("$(PREFIX)/bin/nc-config" --has-nc4)" = yes
	@test -f "$(PREFIX)/include/netcdf.mod"

help:
	@echo 'make [all|zlib|hdf5|netcdf-c|netcdf-fortran|verify] JOBS=4'
	@echo 'Overrides: PREFIX=... ARCHIVES=... WORK=... CC=icc FC=ifort F77=ifort'
	@echo 'Logs: $(LOG). Completed stages are tracked in $(STAMP).'
