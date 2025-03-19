from abc import ABC, abstractmethod
from typing import List, Dict

class BaseRule(ABC):
    def __init__(self, collector_results: List[Dict], files: List[str]):
        self.collector_results = collector_results
        self.files = files
    
    @abstractmethod
    def analyze(self) -> List[Dict]:
        pass