Server Witch API
================

![Server Witch logo](serverwitch.png)

This repository contains the necessary files needed to self-host the Server Witch API to connect the Server Witch client to the Server Witch custom GPT. You can find more information about the Server Witch client [here](https://github.com/g33kex/ServerWitch). 

## Deployement

This server is built in python with [Quart](https://quart.palletsprojects.com/en/latest/) and [Hypercorn](https://hypercorn.readthedocs.io/en/latest/index.html), and can be deployed with docker.

You can either deploy the API only, or use the provided docker compose file which includes an nginx frontend. 

### API Only

To build the docker image, run:
```
docker built -d serverwitch-api .
```

Then, run it with:
```
docker run -p 8000:8000 --name serverwitch-api serverwitch-api:latest
```

The server will listen on port 8000 (HTTP). You need to setup your own reverse proxy to support TLS. 

### With nginx

For your convenience, a docker compose file is provided to deploy the Server Witch API behind an nginx proxy, using certbot to obtain TLS certificates. To use it, run:
```
DOMAIN_NAME="example.com" EMAIL_ADDRESS="email@example.com" docker compose up --build
```

Replace `example.com` and `email@example.com` with the domain name and email address you wish to use for the TSL certificate.

## Custom GPT

If you deploy your own Server Witch API, you will also need your own custom GPT that uses your API server. You can make it using the [official GPT editor](https://chat.openai.com/gpts/editor). You can use the provided [prompt][GPT/serverwitch.txt] and [OpenAPI specification](GPT/openapi.yaml) for the Actions. In that file, replace the `url` field with your own domain name.

Note that it is also possible to use any other LLM that can send requests based on the provided OpenAPI specification.

## Building

This project is built with poetry:
```
poetry build
```

To launch the server in debug mode (without Hypercorn):
```
poetry install
poetry run start
```

## Contributing

Contributions are highly appreciated. Please feel free to submit pull requests and bug reports. If you discover a security vulnerability in this software, contact me at g33kex[at]pm[dot]me.
