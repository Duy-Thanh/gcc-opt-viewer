## gcc-opt-viewer

This is the fork of opt-viewer for GCC support

## Usage

- Compile your C/C++ code with GCC compiler option `-fsave-optimization-record`:
```
gcc -c main.c -fsave-optimization-record -o main
```
or
```
g++ -c main.cpp -fsave-optimization-record -o main
```

- First, you need to install [Python](https://www.python.org/). Please download latest version. Make sure that you checked in `Add to PATH` when finishing Python installation

- On Windows, you need to install [Git for Windows](https://gitforwindows.org/). Please download latest version. You can find install instructions on the Internet

- Open `cmd.exe`, then `cd` to whatever location you like to clone this repository, then:

```
git clone https://github.com/Duy-Thanh/gcc-opt-viewer.git
cd gcc-opt-viewer
```

- Installing all requirements for `opt-viewer.py`:
```
pip install -r requirements.txt
```

- Then you can running `opt-viewer.py` like:

```
python.exe opt-viewer.py
```

- Use `-h` for showing help, which contains informations will help you using this tool:
```
usage: opt-viewer.py [-h] [--output-dir OUTPUT_DIR] BUILD_DIR

Parse the output of GCC's -fsave-optimization-record.

positional arguments:
  BUILD_DIR             The directory in which to look for .json.gz files

options:
  -h, --help            show this help message and exit
  --output-dir OUTPUT_DIR
                        The directory to which to write .html output
```

- After running this tools, open the output dir that specified for `--output-dir` parameter, then open `index.html` file

## Example
```
python opt-viewer.py H:\c_project --output-dir H:\opt-analysis
```
