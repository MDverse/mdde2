# MDverse data explorer 2

## Setup environment

We use [uv](https://docs.astral.sh/uv/getting-started/installation/)
to manage dependencies and the project environment.

Clone the GitHub repository:

```sh
git clone https://github.com/MDverse/mdde2.git
cd mdde2
```

Sync dependencies:

```sh
uv sync
```

## Get data and models

```bash
wget ...
wget ...
wget ...
```


## Launch web app

### Developpment mode

To launch the FastAPI web app, run:

```bash
uv run fastapi dev main.py
```

The app should be available at the following URL:

[http://127.0.0.1:8000/](http://127.0.0.1:8000/)


To access the datasets-information search page, add `/search` to the URL:

[http://127.0.0.1:8000/search](http://127.0.0.1:8000/search)


## Production mode

```bash
uv run uvicorn main:app --reload
```
