FROM alpine:3.19
RUN apk add --no-cache sqlite dcron
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
