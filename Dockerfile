FROM alpine:3.7
COPY ./ /opt/src
RUN cd /opt/src && \
apk add --no-cache python3 git build-base && \
pip3 install -r requirements.txt
WORKDIR /opt/src
CMD ["python3", "start.py"]
