from copy import deepcopy

class MemoryStorage:
    def __init__(self):
        self.raw_logs = {}
        self.normalized_logs = {}

    def save_raw(self, raw_event_id:str, raw_event:dict):
        self.raw_logs[raw_event_id] = deepcopy(raw_event)


    def save_normalized(self, event_id:str, normalized_event:dict):
        self.normalized_logs[event_id] = deepcopy(normalized_event)

    def get_raw(self, raw_event_id: str):
        event = self.raw_logs.get(raw_event_id)
        return deepcopy(event) if event is not None else None

    def get_normalized(self,event_id):
        event = self.normalized_logs.get(event_id)
        return deepcopy(event) if event is not None else None