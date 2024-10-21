FROM ubuntu:22.04 AS build
RUN apt-get update -y
RUN apt-get install -y python3.10 python3-pip cmake swig g++ cmake libssl-dev

WORKDIR /app/src
COPY src/requirements.txt .
RUN pip install -r requirements.txt
COPY src /app/src
EXPOSE 8080

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "3"]