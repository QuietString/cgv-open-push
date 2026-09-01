FROM python:3.10-slim

LABEL name="cgv-open-push"

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p /data

VOLUME ["/data"]

ENTRYPOINT ["python"]
CMD ["cgv_open_push_main.py"]

EXPOSE 5000
EXPOSE 8765
