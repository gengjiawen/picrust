FROM python:2-onbuild
RUN pip install . && python scripts/download_picrust_files.py
