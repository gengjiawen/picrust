FROM python:2-alpine
Add ./ /opt/picrust
WORKDIR /opt/picrust
RUN echo "http://dl-8.alpinelinux.org/alpine/edge/community" >> /etc/apk/repositories
RUN apk --no-cache --update-cache add gcc gfortran python python-dev py-pip build-base wget freetype-dev libpng-dev openblas-dev
RUN pip install numpy
RUN pip install . && python scripts/download_picrust_files.py