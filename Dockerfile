FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py ./

RUN mkdir /data
VOLUME ["/data"]

CMD ["python", "main.py"]
