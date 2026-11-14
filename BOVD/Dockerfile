FROM python:3.12-slim
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir cryptography || true
ENV ASTRA_NO_BROWSER=1 ASTRA_BIND=0.0.0.0
EXPOSE 8765
CMD ["python", "-m", "astra.server"]
