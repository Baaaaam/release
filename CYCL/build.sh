#!/bin/bash
set -x 
set -e

if [[  `uname` == 'Linux' ]]; then
    chmod 755 Miniconda-3.0.5-Linux-x86_64.sh
    ./Miniconda-3.0.5-Linux-x86_64.sh -b -p ./anaconda
    anaconda/bin/conda install patchelf
    cd  git
    make configure 
	 ./configure --prefix=`pwd`/../install
	 make
	 make install
    cd ..
    PATH=$PATH:`pwd`/install/bin
else
    chmod 755 Miniconda-3.0.5-MacOSX-x86_64.sh
    ./Miniconda-3.0.5-MacOSX-x86_64.sh -b -p ./anaconda
fi

mv condarc $HOME/.condarc
anaconda/bin/conda search
anaconda/bin/conda install binstar  
anaconda/bin/conda install conda-build
anaconda/bin/conda install jinja2
anaconda/bin/conda install setuptools
anaconda/bin/conda build --no-test lapack
anaconda/bin/conda install --use-local lapack
anaconda/bin/conda build --no-test coin
anaconda/bin/conda install --use-local coincbc
anaconda/bin/conda build --no-test cyclus
anaconda/bin/conda install --use-local cyclus
tar -czf results.tar.gz anaconda

cp -r anaconda/conda-bld/work/tests cycltest


#build Doc
if [[  `uname` == 'Linux' ]]; then

cd anaconda/conda-bld/work/build
make cyclusdoc | tee  doc.out
line=`grep -i warning doc.out|wc -l`
if [ $line -ne 0 ]
 then
    exit 1
fi
ls -l
mv doc ../../../../cyclusdoc
cd ../../../..
fi

#Regression Testing
anaconda/bin/conda install nose
anaconda/bin/conda install numpy
anaconda/bin/conda install cython
anaconda/bin/conda install numexpr
anaconda/bin/conda install pytables

