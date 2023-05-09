from injector import Module, provider, singleton
from agent_manager import AgentManager
from config_manager import ConfigManager

config = ConfigManager('config.json')

class AgentManagerModule(Module):

    @provider
    @singleton
    def provide_agent_manager(self) -> AgentManager:
        return AgentManager(config.get('agents_path'))
