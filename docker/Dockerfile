FROM osgeo/gdal:latest
MAINTAINER jlinick@mit.edu

# Set the working directory
ENV WORKDIR=/workdir
WORKDIR ${WORKDIR}
ENV HOME=${WORKDIR}

# Set the data directory
ENV DATA=/data

RUN apt-get update && apt-get install -y \
    zip unzip git vim python3-pip tmux wget curl \
    gdal-bin jupyter aria2 \
    imagemagick ffmpeg \
    software-properties-common python3-distutils

RUN pip3 install \
    numpy scipy boto3 matplotlib h5py pyproj fiona \
    scikit-learn scikit-image tqdm pint pymp-pypi \
    pint cvxopt xarray pylint pandas pillow geopandas \
    netcdf4 setuptools===49.6.0 dask toolz opencv-python

# install conda
#RUN curl -LO https://repo.anaconda.com/miniconda/Miniconda3-py39_4.10.3-Linux-x86_64.sh
#RUN bash Miniconda3-py39_4.10.3-Linux-x86_64.sh -p /miniconda -b
#ENV PATH=/miniconda/bin:${PATH}
#RUN conda update -y conda
#RUN conda install -y cartopy

#clone SSARA
#RUN git clone https://www.unavco.org/gitlab/unavco_public/ssara_client.git /SSARA

#ASF HYP3
#RUN git clone https://github.com/ASFHyP3/hyp3-sdk.git /hyp3-sdk
#RUN python3 /hyp3-sdk/setup.py install 
RUN pip3 install hyp3_sdk

# copy current repo
COPY ./ /hyp3_timeseries

RUN echo "PS1='🐳 \e[1;32m\]\u@\e[m\]\e[1;31m\]\h\e[m\]:\e[1;34m\]\w\e[m\]\\$ '" >> ~/.bashrc
