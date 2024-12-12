FROM python:3.12-slim
EXPOSE 8000

COPY . /numerous-apps
RUN pip install -e /numerous-apps

COPY examples/numerous/requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

COPY examples/numerous /app

WORKDIR /app

CMD ["numerous-server", "app.py:app", "--host", "0.0.0.0"]