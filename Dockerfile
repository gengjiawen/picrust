FROM python:2
ADD ./ /app
WORKDIR /app
RUN apt-get update && apt-get install -y libblas-dev liblapack-dev liblapacke-dev gfortran libhdf5-dev
RUN pip install numpy
RUN pip install . && python scripts/download_picrust_files.py