FROM python:3.10-slim

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY . .

# O Hugging Face exige que o app rode na porta 7860
CMD ["gunicorn", "app:server", "--bind", "0.0.0.0:7860"]