FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY env ./env
COPY scripts ./scripts
COPY tests ./tests
COPY app.py ./app.py
COPY dataqa_bench_ui_spec.html ./dataqa_bench_ui_spec.html
COPY openenv.yaml ./openenv.yaml
COPY README.md ./README.md

ENV PYTHONUNBUFFERED=1

EXPOSE 7860

ENV ENABLE_WEB_INTERFACE=true
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]
