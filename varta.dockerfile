FROM python:3.11.9-bookworm

WORKDIR /usr/src/varta

RUN pip install --no-cache-dir prometheus-client == 0.23.1;

COPY ./varta.py ./

EXPOSE 8000/tcp
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# ENTRYPOINT: zusätzliche Argumente von `docker run` werden an varta.py übergeben
ENTRYPOINT [ "python" , "varta.py"]