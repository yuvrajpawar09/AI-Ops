FROM python:3.11-slim

WORKDIR /app

# The default PyPI torch wheel bundles CUDA libraries this CPU-only laptop
# service will never use, adding 1GB+ to the image for nothing. Installing
# the CPU-only build first means the later `pip install -r requirements.txt`
# sees the same version already satisfied and skips re-downloading it.
COPY requirements.txt .
RUN pip install --no-cache-dir torch==2.3.1 --index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
