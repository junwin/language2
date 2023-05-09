# container_config.py

from injector import Injector
from agent_manager_module import AgentManagerModule
from prompts_module import PromptsModule

def configure_container():
    container = Injector([AgentManagerModule(), PromptsModule()])
    return container

container = configure_container()