FROM python:3.12-slim
RUN python -m compileall -q /usr/local/lib/python3.12
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY app.py /app/app.py
EXPOSE 8080
CMD ["python", "/app/app.py"]
