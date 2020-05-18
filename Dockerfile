FROM alpine:3.7
apk add --no-cache python3 git
pip3 install -r requirements.txt
WORKDIR /opt
CMD ["python3", "start.py"]
