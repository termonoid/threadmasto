import time
import logging
from typing import List, Dict

import yaml

from exceptions import InvalidConfig
import modules


class Bridge:
    """связываем место тыбзинга и место постинга"""
    source: modules.Source
    destination: modules.Destination
    last_activation: float
    interval: int

    def __init__(self,
                 source: modules.Source,
                 destination: modules.Destination,
                 period: int):
        print(source, destination, period)
        self.source = source
        self.destination = destination
        self.last_activation = time.time()
        self.interval = period

    def time_to_activation(self) -> float:
        now = time.time()
        activation = self.last_activation + self.interval
        return activation - now

    def activate(self):
        now = time.time()
        posts = self.source.get(self.last_activation)
        self.last_activation = now
        for p in posts:
            self.destination.publish(p)

    def ready(self) -> bool:
        return self.time_to_activation() <= 0


class BridgeConfig:
    "сюда буим парсить короче"
    sources: Dict[str, modules.Source] = {}
    destinations: Dict[str, modules.Destination] = {}
    raw_bridges: List[Dict] = []

    def __init__(self, file_name: str):
        with open(file_name) as file:
            config_dict: dict = yaml.safe_load(file)

        if "sources" in config_dict:
            print(config_dict)
            for name, source in config_dict["sources"].items():
                path = f"{file_name}/sources/{name}"
                try:
                    type = source["type"]
                    print(modules.sources[type](source))
                    self.sources[name] = modules.sources[type](source)
                except InvalidConfig as e:
                    e.file = path
                    raise e
                except KeyError:
                    raise InvalidConfig("No 'type' field.", path)

        if "destinations" in config_dict:
            for name, destination in config_dict["destinations"].items():
                path = f"{file_name}/destinations/{name}"
                try:
                    type = destination["type"]
                    self.destinations[name] = \
                        modules.destinations[type](destination)
                except InvalidConfig as e:
                    e.file = path
                    raise e
                except KeyError:
                    raise InvalidConfig("No 'type' field.", path)

        if "bridges" in config_dict:
            self.raw_bridges = config_dict["bridges"]

    def make_bridges(self) -> List[Bridge]:
        "нельзя создавать мосты до того,"
        "как все конфиги будут считаны"
        "к тому же класс конфига будет не нужен"
        bridges = []
        for b in self.raw_bridges:
            try:
                source = self.sources[b['source']]
                destination = self.destinations[b['destination']]
                interval = b['interval']
            except KeyError as e:
                logging.fatal(f"Invalid bridge definition. "
                              f"Missing field {e.args[0]}")
                raise InvalidConfig("Bad bridge")
            bridges.append(Bridge(source, destination, interval))
        return bridges

    def update(self, other: 'BridgeConfig'):
        self.sources.update(other.sources)
        self.destinations.update(other.destinations)
        self.raw_bridges.extend(other.raw_bridges)
        return self
