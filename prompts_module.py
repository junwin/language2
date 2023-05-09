from injector import Module, provider, singleton
from prompts import Prompts
from config_manager import ConfigManager

config = ConfigManager('config.json')


class PromptsModule(Module):

    @provider
    @singleton
    def provide_prompts(self) -> Prompts:
        return Prompts(config.get('preset_path'))
