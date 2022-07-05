# NATHacks 2022 - Python Boiler

**TODO: A short blob on what the project is**


## Motivation

**TODO: What is the project for? And Why?**


## Installation

### Requirements

- [Python](https://www.python.org/downloads/) 3.9 or above
- [virtualenv](https://docs.python.org/3/library/venv.html)
- Jupyter???


### Build From Source

Clone the repository
```sh
git clone https://github.com/neuralbertatech/natHACKS_2022_Python_Boiler
```

Create a virtual environment to install the dependencies
```sh
python -m venv <Environment-Name>  # For example  $ python -m venv python_boiler
```

Activate the virtual environment and install the dependencies
```sh
./<Environment-Name>/Scripts/activate  # ./python_boiler/Scripts/activate
pip install -r requirements.txt
```


## Getting Started

**TODO: Add a section for each use case**


## TODO

### Issues

```sh
$ python .\arduino_windows.py
Traceback (most recent call last):
  File "C:\Users\zrsel\code\git\natHACKS_2022_Python_Boiler\test_python_boiler\lib\site-packages\pygatt\backends\bgapi\bgapi.py", line 32, in <module>
    import termios
ModuleNotFoundError: No module named 'termios'

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "C:\Users\zrsel\code\git\natHACKS_2022_Python_Boiler\arduino_windows.py", line 4, in <module>
    import pygatt
  File "C:\Users\zrsel\code\git\natHACKS_2022_Python_Boiler\test_python_boiler\lib\site-packages\pygatt\__init__.py", line 14, in <module>
    from .backends import BGAPIBackend, GATTToolBackend, BLEAddressType  # noqa
  File "C:\Users\zrsel\code\git\natHACKS_2022_Python_Boiler\test_python_boiler\lib\site-packages\pygatt\backends\__init__.py", line 2, in <module>
    from .bgapi.bgapi import BGAPIBackend  # noqa
  File "C:\Users\zrsel\code\git\natHACKS_2022_Python_Boiler\test_python_boiler\lib\site-packages\pygatt\backends\bgapi\bgapi.py", line 36, in <module>
    BGAPIError, serial.serialutil.SerialException)
AttributeError: module 'serial' has no attribute 'serialutil'
```

```sh
$ python .\baseline_window.py
Traceback (most recent call last):
  File "C:\Users\zrsel\code\git\natHACKS_2022_Python_Boiler\baseline_window.py", line 339, in <module>
    win = baseline_win()
  File "C:\Users\zrsel\code\git\natHACKS_2022_Python_Boiler\baseline_window.py", line 72, in __init__
    self.csv_name = csv_name[:-4] + "_" + str(int(time.time())) + ".csv"
TypeError: 'NoneType' object is not subscriptable
```

```sh
$ python .\graph_window.py
Logger: GraphWindow: INFO at: 2022-07-04 21:14:45,080, line 28: Program started at 1656990885.079809
INFO:GraphWindow:Program started at 1656990885.079809
Logger: GraphWindow: INFO at: 2022-07-04 21:14:45,896, line 77: Initializing graph_win (Graph window)
INFO:GraphWindow:Initializing graph_win (Graph window)
Traceback (most recent call last):
  File "C:\Users\zrsel\code\git\natHACKS_2022_Python_Boiler\graph_window.py", line 225, in <module>
    win = graph_win()
  File "C:\Users\zrsel\code\git\natHACKS_2022_Python_Boiler\graph_window.py", line 87, in __init__
    self.board = Board(data_type, hardware, model, board_id)
  File "C:\Users\zrsel\code\git\natHACKS_2022_Python_Boiler\Board.py", line 36, in __init__
    assert self.board_id is not None, "Error: Undefined combination of arguments passed to 'get_board_id'"
AssertionError: Error: Undefined combination of arguments passed to 'get_board_id'
```

```sh
$ python .\impedance_window.py
Traceback (most recent call last):
  File "C:\Users\zrsel\code\git\natHACKS_2022_Python_Boiler\impedance_window.py", line 390, in <module>
    win = impedance_win()
  File "C:\Users\zrsel\code\git\natHACKS_2022_Python_Boiler\impedance_window.py", line 112, in __init__
    if self.data_type == "Task live":
AttributeError: 'impedance_win' object has no attribute 'data_type'
```

```sh
$ python .\main_menu.py
Logger: MenuWindow: INFO at: 2022-07-04 21:16:35,431, line 90: Program started at 1656990995.4310365
INFO:MenuWindow:Program started at 1656990995.4310365
Logger: GraphWindow: INFO at: 2022-07-04 21:16:35,457, line 28: Program started at 1656990995.4570363
INFO:GraphWindow:Program started at 1656990995.4570363
Traceback (most recent call last):
  File "C:\Users\zrsel\code\git\natHACKS_2022_Python_Boiler\test_python_boiler\lib\site-packages\pygatt\backends\bgapi\bgapi.py", line 32, in <module>
    import termios
ModuleNotFoundError: No module named 'termios'

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "C:\Users\zrsel\code\git\natHACKS_2022_Python_Boiler\main_menu.py", line 104, in <module>
    from arduino_windows import ard_wind_on as ard_turn_on
  File "C:\Users\zrsel\code\git\natHACKS_2022_Python_Boiler\arduino_windows.py", line 4, in <module>
    import pygatt
  File "C:\Users\zrsel\code\git\natHACKS_2022_Python_Boiler\test_python_boiler\lib\site-packages\pygatt\__init__.py", line 14, in <module>
    from .backends import BGAPIBackend, GATTToolBackend, BLEAddressType  # noqa
  File "C:\Users\zrsel\code\git\natHACKS_2022_Python_Boiler\test_python_boiler\lib\site-packages\pygatt\backends\__init__.py", line 2, in <module>
    from .bgapi.bgapi import BGAPIBackend  # noqa
  File "C:\Users\zrsel\code\git\natHACKS_2022_Python_Boiler\test_python_boiler\lib\site-packages\pygatt\backends\bgapi\bgapi.py", line 36, in <module>
    BGAPIError, serial.serialutil.SerialException)
AttributeError: module 'serial' has no attribute 'serialutil'
```

```sh
$ python .\model_window.py
sampling rate: 250
Traceback (most recent call last):
  File "C:\Users\zrsel\code\git\natHACKS_2022_Python_Boiler\model_window.py", line 345, in <module>
    win = model_win()
  File "C:\Users\zrsel\code\git\natHACKS_2022_Python_Boiler\model_window.py", line 94, in __init__
    self.file_name = parent.csv_name
AttributeError: 'NoneType' object has no attribute 'csv_name'
```

```sh
$ python .\session_window.py
Traceback (most recent call last):
  File "C:\Users\zrsel\code\git\natHACKS_2022_Python_Boiler\test_python_boiler\lib\site-packages\pygatt\backends\bgapi\bgapi.py", line 32, in <module>
    import termios
ModuleNotFoundError: No module named 'termios'

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "C:\Users\zrsel\code\git\natHACKS_2022_Python_Boiler\session_window.py", line 60, in <module>
    import pygatt
  File "C:\Users\zrsel\code\git\natHACKS_2022_Python_Boiler\test_python_boiler\lib\site-packages\pygatt\__init__.py", line 14, in <module>
    from .backends import BGAPIBackend, GATTToolBackend, BLEAddressType  # noqa
  File "C:\Users\zrsel\code\git\natHACKS_2022_Python_Boiler\test_python_boiler\lib\site-packages\pygatt\backends\__init__.py", line 2, in <module>
    from .bgapi.bgapi import BGAPIBackend  # noqa
  File "C:\Users\zrsel\code\git\natHACKS_2022_Python_Boiler\test_python_boiler\lib\site-packages\pygatt\backends\bgapi\bgapi.py", line 36, in <module>
    BGAPIError, serial.serialutil.SerialException)
AttributeError: module 'serial' has no attribute 'serialutil'
```
