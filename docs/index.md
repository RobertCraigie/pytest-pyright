# Welcome to pytest-pyright

pytest-pyright is a [pytest](https://pytest.org/) plugin for type checking code with [pyright](https://github.com/microsoft/pyright).

## Why Should You Use it?

pytest-pyright was created to ensure that complex types are correctly constrained, i.e will raise an error if used incorrectly.

if your project makes use of any complex types you should find some value out pytest-pyright.

## How Does it Work?

pytest-pyright collects all python files in a `typesafety` directory relative to wherever you run pytest from, the location of this directory can be changed with the `--pyright-dir` pytest option.

The collected files are all type checked individually using [pyright](https://github.com/microsoft/pyright), if no errors ocurr then the all tests will pass!

However this is not very useful, keep reading to find out how to assert that an error is raised and check variable types.

## Checking for Errors

You can check that certain lines in a file raise an error by adding a comment, e.g.

```py
--8<-- "docs/src/index/errors.py"
```

## Checking Types

You can check that the type of a certain variable is what you expect it to be, e.g.

```py
--8<-- "docs/src/index/types.py"
```

## Unexpected Errors

If any unexpected errors are raised by pyright, any calls to `reveal_type` are missing a type comment or any other error, the test will fail and something like the following will be displayed.

```
--8<-- "docs/src/index/error.txt"
```
