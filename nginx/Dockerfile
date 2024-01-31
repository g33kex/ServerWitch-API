# Use Nginx image based on Debian Slim
FROM nginx:1.25-bookworm

ARG DOMAIN
ENV DOMAIN=${DOMAIN}

ARG EMAIL
ENV EMAIL=${EMAIL}

# Update packages and install necessary tools
RUN apt update \
    && apt-get install --no-install-recommends -y certbot openssl cron \
    # Cache cleanup
    && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
    && apt-get clean -y && rm -rf /var/lib/apt/lists/*

WORKDIR /opt

# Copy scripts
COPY certbot.sh certbot-cron ./
COPY entrypoint.sh nginx-letsencrypt
COPY default.conf /etc/nginx/conf.d/default.conf
COPY ip-whitelist.conf /etc/nginx/ip-whitelist.conf
COPY real-ip.conf /etc/nginx/conf.d/

RUN chmod +x nginx-letsencrypt && \
    chmod +x certbot.sh

# Set entrypoint
ENTRYPOINT ["./nginx-letsencrypt"]

EXPOSE 80 443