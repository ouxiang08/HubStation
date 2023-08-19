FROM python:3.10

LABEL name="HubStation"
LABEL version="0.0.1"
LABEL description="HubStation"

WORKDIR /app

ADD . ./

# CMD ["python"]