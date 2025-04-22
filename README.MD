# O que é?

Dolfi é uma aplicação desenvolvida em Python, que possui 2 frentes: ela primeiramente é uma buscadora de carteiras rentáveis em suas transações de Bitcoin, e a sua segunda função é disponibilizar essas carteiras para o público. No repositório você encontrará apenas o código da API da segunda função, visite nosso site neste link: [www.dolfi.cc](www.dolfi.cc)

## As rotas de Dolfi

### /all - GET

Nesta requisição serão retornadas todas as carteiras presentes na base de dados de Dolfi.
Exemplo:

```json
[
{
"address": "<address>",
"balance_btc": 0.01129175,
"balance_usd": 958.98,
"roa": 33.258
}, 
]
```

### /:address - GET, POST, DELETE

#### GET

Nesta requisição serão retornados os dados de uma carteira presente na base de dados Dolfi. Exemplo:

```json
{
"address": "<address>",
"balance_btc": 0.01129175,
"balance_usd": 958.98,
"first_transaction_date": "23/03/2024, 23:41:47",
"roa": 33.258,
"transaction_count": 311
}
```

#### POST

Nesta requisição serão computados os dados e transações da carteira enviada, e armazenados na base de dados de Dolfi.

```json
{
"message": "Carteira inserida e dados calculados."
}
```

#### DELETE

Nesta requisição serão deletados os dados e transações da carteira em questão da base de dados de Dolfi. Exemplo:

```json
{
"message": "Carteira <address> removida."
}
```

### /txs/:address/:page - GET

Nesta requisição serão retornados os dados das transações da carteira em questão, sendo retornadas 20 transações, cada página se refere a uma divisão ordenada de 20 transações, que se seguem. Exemplo:

```json
[
{
"balance_btc": -0.00010639,
"balance_usd": -8.79,
"is_incoming": false,
"transaction_date": "09/04/2025, 17:03:58",
"transaction_id": "<transaction_id>",
"wallet_address": "<address>"
}, 
]
```

## Tecnologias utilizadas

- A aplicação é desenvolvida em **Flask**
- A aplicação é hospedada com **Gunicorn**
- Containerizada com **Docker**
- O banco de dados utilizado é **PostgreSQL**
- Banco de dados gerenciado por **SQLAlchemy ORM**
- Serialização e deserialização de Models **SQLAlchemy ORM** com **Marshmallow**
- Cache das rotas é armazenado em **Redis**
- Processamento assíncrono com **Celery**, com mensageria e backend de resultados **Redis**
- Implementação de logging com **Logoru**
