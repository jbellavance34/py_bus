# Project python bus

The pybus.py script parse the St-Jean-Sur-Le-Richelieu autobus timeline.

## api call

    * /          - return all bus trajectories ( sjsr and mtrl) and max 10
    * ?dest=sjsr - return only sjsr bus trajectories (combines with max=x)
    * ?dest=mtrl - return only mtrl bus trajectories (combines with max=x)
    * ?max=x     - return only x bus trajectories (combines with ?dest=value)

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

* http://python.org/
* https://www.flaskapi.org/
* https://serverless.com/
* https://aws.amazon.com/