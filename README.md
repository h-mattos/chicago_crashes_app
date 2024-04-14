# Chicago Crashes App
Demo app that shows the expected risk and severity of a car crash in a route in city of Chicago.
## VERY IMPORTANT
This app uses [OpenStreetMap's Nominatim](https://nominatim.openstreetmap.org) to query latitude and longitude from a given address. As such, it is very important to adhere to their [Usage Policy](https://operations.osmfoundation.org/policies/nominatim/). Since this app is a demo, there are still some features that are still missing, like caching already searched locations, so if you are testing this app, try to search for a different address every time to avoid being banned.
## TL;DR
If you just want to run the app follow these steps:

- Clone the repo with `git clone`.
- Create an environmet either with `virtualenv`, `venv` or `conda create`.
- Go to the root folder where `app.py` is located.
- Install required packages with `pip install -r requirements`.
- Run app with `flet run app.py`.

## Pre-compiled binaries
We have precompiled the binaries for Windows(x64). This was done using the command in the __Compiling__ section. Nonetheless, we recomend creating a Python=3.10 environment and installing the requirements to run it in interactive mode to catch any warning or error.
## Compiling
You can compile the code yourself with the folloing command.
```
flet pack --hidden-import=pyarrow.vendored.version app.py
```
## Running from a Python environment
From within a Python environment (or Conda environment) install the required packages:
```
pip install -r requirements.txt
```

Then you can run the app with the command:
```
flet run app.py
```

Or you can just run the code withing app.py
## Considerations
Since this is a demo, there are some things that are open to change. Here are some:

- The model behind the risk prediction is trained with [Catboost](http://catboost.ai/). So the code expects a .cbm file.
- As stated in the __Important__ section, you might get temporally banned and the app won't work.
- If you write an address that is not found with OpenStreetMap, the app might crash.
