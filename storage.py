from copy import deepcopy

class MemoryStorage:
    def __init__(self):
        self.raw_logs = {}
        self.normalized_logs = {}
        self.sources = {}

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

    def add_source(self, source: dict):
        source_id = source["source_id"]
        source_name = source["name"].casefold()

        for existing_source in self.sources.values():
            if existing_source["name"].casefold() == source_name:
                raise ValueError ("Source name already exists.")

        self.sources[source_id] = deepcopy(source)
        return deepcopy(source)

    def list_sources(self):
        return deepcopy(list(self.sources.values()))

    def get_source(self,source_id: str):
        source = self.sources.get(source_id)
        return deepcopy(source) if source is not None else None

    def get_source_by_name(self,name:str):
        target_name = name.strip().casefold()

        for source in self.sources.values():
            if source["name"].casefold() == target_name:
                return deepcopy(source)
        return None