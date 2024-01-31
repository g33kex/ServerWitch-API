#!/bin/bash
# Create a self signed default certificate, so Ngix can start before we have
# any real certificates.

mkdir -p /usr/share/nginx/certificates

### If certificates don't exist yet we must ensure we create them to start nginx
if [[ ! -f /usr/share/nginx/certificates/fullchain.pem ]]; then
    openssl genrsa -out /usr/share/nginx/certificates/privkey.pem 4096
    openssl req -new -key /usr/share/nginx/certificates/privkey.pem -out /usr/share/nginx/certificates/cert.csr -nodes -subj \
    "/C=PT/ST=World/L=World/O=${DOMAIN}/OU=serverwitch lda/CN=${DOMAIN}/EMAIL=${EMAIL}"
    openssl x509 -req -days 365 -in /usr/share/nginx/certificates/cert.csr -signkey /usr/share/nginx/certificates/privkey.pem -out /usr/share/nginx/certificates/fullchain.pem
fi

# Start the cron service
cron

# Load the crontab file
crontab /opt/certbot-cron

# Download additional Let's Encrypt configurations if not already present
if [ ! -f "/etc/ssl-options/options-nginx-ssl.conf" ]; then
    curl -L --create-dirs -o "/etc/ssl-options/options-nginx-ssl.conf" \
         https://raw.githubusercontent.com/certbot/certbot/master/certbot-nginx/certbot_nginx/_internal/tls_configs/options-ssl-nginx.conf
fi

if [ ! -f "/etc/ssl-options/ssl-dhparams.pem" ]; then
    openssl dhparam -out "/etc/ssl-options/ssl-dhparams.pem" 2048
fi

#Run the command once for certificate generation
/opt/certbot.sh &

# Start Nginx with daemon off
nginx -g "daemon off;"