FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml ./
COPY outlier ./outlier
RUN pip install --no-cache-dir -e .
ENV OUTLIER_HOST=0.0.0.0 OUTLIER_DATA_DIR=/data
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "outlier.main:app", "--host", "0.0.0.0", "--port", "8000"]
