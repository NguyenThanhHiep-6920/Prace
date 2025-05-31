###############################################################
#
# Zero phase
#
###############################################################
FROM python:3.10.13-slim AS pythonbase


# instalace curl, aby bylo mozne zprovoznit standardni healthcheck
RUN apt update && apt install curl -y && rm -rf /var/cache/apk/*

# Install pip requirements
COPY ./requirements.txt .
RUN python -m pip install -r requirements.txt

###############################################################
#
# Last phase
#
###############################################################
FROM pythonbase as executepython

EXPOSE 8000

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

#ENV PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus_multiproc_dir

WORKDIR /app
COPY . /app

# Phải tạo thư mục khi còn root
# RUN mkdir -p /tmp/prometheus_multiproc_dir && chmod 777 /tmp/prometheus_multiproc_dir && \
#     useradd appuser && chown -R appuser /app

# Creates a non-root user and adds permission to access the /app folder
# For more info, please refer to https://aka.ms/vscode-docker-python-configure-containers
RUN useradd appuser && chown -R appuser /app
USER appuser

#USER 1000


# During debugging, this entry point will be overridden. For more information, please refer to https://aka.ms/vscode-docker-python-debug
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "-k", "uvicorn.workers.UvicornWorker", "server.main:app"]
#CMD ["gunicorn", "--reload", "--reload-engine", "inotify", "--bind", "0.0.0.0:8000", "-k", "uvicorn.workers.UvicornWorker", "app:app"]
