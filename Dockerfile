FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 MPLCONFIGDIR=/tmp/matplotlib CANON_RESULTS_DIR=/data/results
COPY requirements-lock.txt ./
RUN pip install --no-cache-dir -r requirements-lock.txt
COPY canon ./canon
COPY configs ./configs
COPY web ./web
COPY main-2.py ./
COPY results/advanced-confirmation ./results/advanced-confirmation
COPY scripts/start-server.py ./scripts/start-server.py
EXPOSE 8765
CMD ["python", "scripts/start-server.py"]
