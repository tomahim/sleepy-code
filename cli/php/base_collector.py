from abc import ABC, abstractmethod
import json
from typing import List, Dict

class BaseCollector(ABC):
    def __init__(self, files: List[str]):
        self.files = files
        
    @abstractmethod
    def collect(self) -> List[Dict]:
        """
        Must be implemented by concrete collectors
        Returns a list of collected items in dictionary format
        """
        pass

    def output_json(self) -> str:
        """
        Returns the collected data as JSON string
        """
        return json.dumps(self.collect(), indent=4)