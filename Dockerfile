FROM alpine:3.7
COPY ./ /opt/src
apk add --no-cache python3 git
cd /opt/src && \
pip3 install -r requirements.txt
WORKDIR /opt
CMD ["python3", "/opt/src/start.py"]
