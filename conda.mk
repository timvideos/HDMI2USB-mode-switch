# Makefile to setting up a conda environment.
export PATH := $(PWD)/conda/bin:$(PATH)

Miniconda3-latest-Linux-x86_64.sh:
	wget -c https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh -O .Miniconda3-latest-Linux-x86_64.sh
	mv -f .Miniconda3-latest-Linux-x86_64.sh Miniconda3-latest-Linux-x86_64.sh

conda/bin/conda: Miniconda3-latest-Linux-x86_64.sh
	chmod a+x Miniconda3-latest-Linux-x86_64.sh
	./Miniconda3-latest-Linux-x86_64.sh -p conda -b

conda/.condarc:
	conda config --system --set always_yes yes --set changeps1 no
	conda config --system --add channels timvideos

conda/bin/%: conda/bin/conda
	conda install $(shell basename $@)

conda/.modules/%: conda/bin/conda
	mkdir -p $(shell dirname $@)
	pip install $(shell basename $@)
	touch $@

PYTHON_MODULES = pyusb pep8 autopep8 setuptools-pep8

DEPS := \
	$(foreach P,$(PYTHON_PACKAGES),conda/.modules/$(P)) \
	$(foreach P,$(CONDA_PACKAGES),conda/bin/$(P))

conda: $(DEPS)
	@true

check-conda:
	[ -d conda ]

clean-conda:
	rm -rf Miniconda3-latest-Linux-x86_64.sh
	rm -rf conda

.PHONY: check-conda clean-conda
