FROM python:3.8-alpine
COPY ./ /opt/src
RUN cd /opt/src && \
apk add --no-cache python3 git build-base gcc musl-dev libffi-dev && \
pip3 install -r requirements.txt
WORKDIR /opt/src
CMD ["python3", "start.py"]
