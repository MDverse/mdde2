# MDverse data explorer 2

## Setup environment

We use [uv](https://docs.astral.sh/uv/getting-started/installation/)
to manage dependencies and the project environment.

Clone the GitHub repository:

```sh
git clone git@github.com:MDverse/mdde2.git
cd mdde2
```

Sync dependencies:

```sh
uv sync
```


## Launch web page

To launch the web page, run the following command:

```sh
uv run uvicorn main:app --reload
```

The web page should be available at the following URL:

[http://127.0.0.1:8000/](http://127.0.0.1:8000/)

If not just click on the URL provided by the terminal.