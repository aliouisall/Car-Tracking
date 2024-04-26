# Car Tracking
## About the project

A tool for traffic analysis.

## Built with

[![Python][Python.py]][Python-url]

## Installation

Install dependencies :
```sh
    pip install -r requirements.txt
```

## Usage

Docker compose :
```sh
    docker-compose up -d
```

Run server :
```sh
    python server.py
```

Database connection :
```sh
    docker exec -it vehdetect-postgresql psql -U vehdetect -d vehdetect
```

Unit test :
```sh
    python -m unittest test_server.py
```

Stop services :
```sh
    docker stop vehdetect-postgresql
```

Stop and delete container :
```sh
    docker-compose down
```

<!-- MARKDOWN LINKS & IMAGES -->

[Python.py]: https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white
[Python-url]: https://www.python.org/
