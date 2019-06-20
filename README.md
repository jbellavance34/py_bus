# Project python bus

The pybus.py script parse the St-Jean-Sur-Le-Richelieu autobus timeline.

## api call

    * /          - return all bus trajectories ( sjsr and mtrl)
    * /dest=sjsr - return only sjsr bus trajectories 
    * /dest=mtrl - return only mtrl bus trajectories

## Requirements

Install the required python packages

```bash
pip install --no-cache-dir -r requirements.txt
```

## Running the tests

```bash
python pybus_test.py -v
```

## Authors

* **Jeremie Bellavance** - *Maintainer*


## Acknowledgments

* http://python.org
