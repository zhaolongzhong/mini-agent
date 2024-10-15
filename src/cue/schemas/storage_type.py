from enum import Enum


class StorageType(Enum):
    IN_MEMORY = "in_memory"
    FILE = "file"
    DATABASE = "database"
