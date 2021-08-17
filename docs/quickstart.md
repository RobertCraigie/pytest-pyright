# Quickstart

!!! note
    This tutorial does not actually do anything meaningful and is just meant to show how to get `pytest-pyright` up and running.

In a new directory, create and activate a virtualenv

```sh
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies

```sh
pip install -U pytest pytest-pyright
```

Create a typesafety directory

```sh
mkdir typesafety
```

Create a new file in your editor at `typesafety/quickstart.py` and copy paste the content below:

```py
--8<-- "docs/src/quickstart.py"
```

Run pytest

```sh
pytest
```
```
============================test session starts ============================
platform darwin -- Python 3.10.0b4, pytest-6.2.4, py-1.10.0, pluggy-0.13.1
rootdir: /Users/robert/tmp/pytest-pyright-quickstart
plugins: pyright-0.0.1
collected 1 item

typesafety/quickstart.py .                                            [100%]

============================ 1 passed in 2.43s =============================
```
