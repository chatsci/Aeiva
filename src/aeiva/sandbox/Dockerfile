FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt
COPY . /app

CMD ["uvicorn", "sandbox:app", "--host", "0.0.0.0", "--port", "8000"]