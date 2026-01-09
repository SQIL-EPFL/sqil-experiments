# sqil-experiments
The repository for measurements and data analysis of SQIL @ EPFL

## Installation
If you have already installed python 3.12 and poetry skip to step 6.

**1. Get the right python**  
Install python > 3.12 from the official website (no, your anaconda is not enough)
During installation, make sure to select the option to add python to your PATH

**2. Install pipx globally**  
Open a command prompt and run
```bash
pip install --user pipx
python -m pipx ensurepath
```

3. **Install poetry globally**  
```bash
python -m pipx install poetry
python -m pipx ensurepath
```

Close the prompt and open a new one.  
You can now use poetry and pipx globally.

**4. Install poetry shell**
```bash
pip install poetry-plugin-shell
```

**5. Install ipython and jupyter**
```bash
pip install jupyter ipykernel
```

**6. Install the required packages using poetry**
```bash
poetry install --no-root
```

**7. Install the pre-commit hooks**
   If you are on windows you need to install git ([https://git-scm.com/downloads](here)) and add it to your windows PATH.
   After the installation open a new terminal.

```bash
poetry run pre-commit install
```

This will check if your python files are formatted correctly when you try to commit.
If that's not the case the commit will be canceled and the files will be automatically formatted.
Then you'll have to add and commit again the new files.

**8. Start the virtual environment**

```bash
poetry shell
```

The first time you might need to manually install qt bindings. They are required for plottr, but cannot be shipped with the package. Make sure to be in the poetry environment and run the following

```bash
pip install pyqt5
```

To exit the virtual environment just use `exit`

## Usage

### 0. Prepare a measurement folder
- Create a folder where you'll store the measurement code and setup
- Copy the contents of `get_started/` in your new folder

### 1. Setup
Navigate to `./setup` and find the setup file that more closely resembles your
usecase, or create a new one.  

**Data storage**
- Change `data_folder_name` to the name of your cooldown
- If needed, update the database folder names `db_root` and `db_root_local`

**QPU**
- Choose the right number of qubits `n_qubits`
- Make sure you're using the appropriate qubit class
- Choose initial qubit parameters reasonably close to the expected ones (optional)

**Zurich Instruments**
- Make sure `generate_zi_setup` contains the correct IDs and options

**Other instruments**
- Check all the IP addresses
- Choose the appropriate default values
- Make sure all the `variable` bindings point to the right parameter

### 2. Config
- Specify the relative path to the setup file you want to use in `config.yaml`
- Choose the desired log level (amount of information printed during measurements)

### 3. Measure
- Choose the sqil experiments poetry environment as your kernel for `measure.ipynb`
- Run measurements
- The first measurement will generate your QPU in the local db folder