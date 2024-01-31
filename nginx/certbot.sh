#!/bin/bash
# Renew certificate and reload Nginx if successful

# Wait a bit for nginx to start in the other script (else it fails)
sleep 15

mkdir -p /var/www/certbot

{
    echo "Attempting to renew certificate..."
    certbot certonly \
     --config-dir ${LETSENCRYPT_DIR:-/etc/letsencrypt} \
     --agree-tos \
     --email ${EMAIL} \
     --no-eff-email \
     --webroot \
     --webroot-path=/var/www/certbot \
     --noninteractive \
     --reinstall \
     -d ${DOMAIN}
     $OPTIONS || true

    if [[ -f "${LETSENCRYPT_DIR:-/etc/letsencrypt}/live/$DOMAIN/fullchain.pem" ]]; then
        cp "${LETSENCRYPT_DIR:-/etc/letsencrypt}/live/$DOMAIN/privkey.pem" /usr/share/nginx/certificates/privkey.pem
        cp "${LETSENCRYPT_DIR:-/etc/letsencrypt}/live/$DOMAIN/fullchain.pem" /usr/share/nginx/certificates/fullchain.pem

        nginx -s reload
    fi
} >> /var/log/certbot-cron.log 2>&1

