<img src="https://neuralberta.tech/images/event/natHACKs/nathanGlow.png" height="250">

# NATHacks 2022 - Python Boiler

This is a collection of tools created to help jumpstart users on working with BCI hardware.


## Installation

### Requirements

- [Python](https://www.python.org/downloads/) 3.9 or above
- [virtualenv](https://docs.python.org/3/library/venv.html)
- All requirements within requirements.txt (refer to above for installation)


### From Source

Clone the repository:
```sh
git clone https://github.com/neuralbertatech/natHACKS_2022_Python_Boiler
cd natHACKS_2022_Python_Boiler
```

Create a virtual environment to install the dependencies:
```sh
python -m venv <Environment-Name>  # For example  $ python -m venv python_boiler
```

Activate the virtual environment and install the dependencies (Platform-Specific):
#### Linux / MacOS (??????)
```sh
./<Environment-Name>/Scripts/activate  # ./python_boiler/Scripts/activate
pip install -r requirements.txt
```

### Windows (Powershell)
```sh
./<Environment-Name>/Scripts/Activate.ps1
pip install -r requirements.txt
```

## Getting Started

Now to get started simply run:
```sh
./main_menu.py
# or
python ./main_menu.py
```

## Known Issues

### AttributeError from 'serial'
```sh
$ python .\main_menu.py
Logger: MenuWindow: INFO at: 2022-07-04 21:16:35,431, line 90: Program started at 1656990995.4310365
INFO:MenuWindow:Program started at 1656990995.4310365
Logger: GraphWindow: INFO at: 2022-07-04 21:16:35,457, line 28: Program started at 1656990995.4570363
INFO:GraphWindow:Program started at 1656990995.4570363
Traceback (most recent call last):
  File ".\natHACKS_2022_Python_Boiler\test_python_boiler\lib\site-packages\pygatt\backends\bgapi\bgapi.py", line 32, in <module>
    import termios
ModuleNotFoundError: No module named 'termios'

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File ".\natHACKS_2022_Python_Boiler\main_menu.py", line 104, in <module>
    from arduino_windows import ard_wind_on as ard_turn_on
  File .\natHACKS_2022_Python_Boiler\arduino_windows.py", line 4, in <module>
    import pygatt
  File ".\natHACKS_2022_Python_Boiler\test_python_boiler\lib\site-packages\pygatt\__init__.py", line 14, in <module>
    from .backends import BGAPIBackend, GATTToolBackend, BLEAddressType  # noqa
  File ".\natHACKS_2022_Python_Boiler\test_python_boiler\lib\site-packages\pygatt\backends\__init__.py", line 2, in <module>
    from .bgapi.bgapi import BGAPIBackend  # noqa
  File ".\natHACKS_2022_Python_Boiler\test_python_boiler\lib\site-packages\pygatt\backends\bgapi\bgapi.py", line 36, in <module>
    BGAPIError, serial.serialutil.SerialException)
AttributeError: module 'serial' has no attribute 'serialutil'
```

This issue occures when you have both serial and pyserial installed on your machine. To resolve run:
```sh
# Remove old serial libraries
pip uninstall serial
pip uninstall pyserial

# Install a fresh version of pyserial
pip install pyserial
```
