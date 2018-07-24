
from core4.config import connect

mongo_url = "mongodb://localhost:27017"  # default mongo connection
mongo_database = "core4dev"  # default core4 system mongo database

kernel = {
    "sys.conf": None,
    "sys.log": None
}

folder = {
    'root': '/srv/core4',
    'transfer': 'transfer',
    'process': 'proc',
    'archive': 'arch',
    'location': 'api/location',
    'upstream': 'api/upstream',
    'vassal': 'api/vassal',
    'temp': 'temp'
}

logging = {
    "stderr": "DEBUG",
    "stdout": None,
    "mongodb": None,
    "format": "%(asctime)s - %(levelname)-8s [%(qual_name)s/%(identifier)s] %(message)s",
    "exception": {
        "capacity": 1000
    },
    "extra": None
}