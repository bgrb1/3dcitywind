FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY locustfile.py locustfile.py
COPY fastutm.py fastutm.py
ENTRYPOINT ["locust"]