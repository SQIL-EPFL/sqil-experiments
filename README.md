# sqil-experiments
The repository for measurements and data analysis of SQIL @ EPFL

## Usage

1. **Install poetry if you haven't already**

```bash
$ pip install poetry
$ pip install poetry-plugin-shell
```

2. **Install the required packages using poetry**

```bash
$ poetry install --no-root
```

3. **Install the pre-commit hooks**
   If you are on windows you need to install git ([https://git-scm.com/downloads](here)) and add it to your windows PATH.
   After the installation open a new terminal.

```bash
$ poetry run pre-commit install
```

This will check if your python files are formatted correctly when you try to commit.
If that's not the case the commit will be canceled and the files will be automatically formatted.
Then you'll have to add and commit again the new files.

4. **Start the virtual environment**

```bash
$ poetry shell
```

To exit the virtual environment just use `exit`