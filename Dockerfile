FROM python:3.7-alpine

COPY requirements.txt /requirements.txt
COPY src/main.py /usr/local/bin/travis-trigger

RUN apk add --no-cache tini \
    && pip install -r requirements.txt \
    && chmod +x /usr/local/bin/travis-trigger \
    && rm /requirements.txt \
    && echo "*/10 * * * * travis-trigger" > /etc/crontabs/root

ENTRYPOINT ["/sbin/tini", "--"]
CMD ["/usr/sbin/crond", "-f", "-d", "8"]
