#import openai
import logging
#from prompt_store import PromptStore
#from prompt_manager import PromptManager

from response_handler import FileResponseHandler
from agent_manager import AgentManager
#from message_preProcess import MessagePreProcess
#from api_helpers import ask_question, get_completion
#from preset_prompts import Prompts
import re
#from injector import Injector
#from container_config import container
from config_manager import ConfigManager 
from message_processor import MessageProcessor


class MessageProcessorStore:
    processors = {}

    def get_message_processor(self, agent_name: str, account_name: str):

        #config = container.get(ConfigManager) 

        #prompt_base_path=config.get('prompt_base_path')  

        processor_name = self.get_processor_name(agent_name, account_name)

        logging.info(f'get_message_processor: {processor_name}')
        #agent_manager = container.get(AgentManager)

        if processor_name not in self.processors:
            
            #agent = agent_manager.get_agent(agent_name)

            #my_handler = FileResponseHandler(agent['max_output_size'])

            #account_prompt_manager = container.get(PromptStore).get_prompt_manager(prompt_base_path, agent_name, account_name, agent['language_code'][:2])
            #agent_prompt_manager = container.get(PromptStore).get_prompt_manager(prompt_base_path, agent_name, "aaaa", agent['language_code'][:2])   


            proc = MessageProcessor(agent_name, account_name)
            self.processors[processor_name] = proc

        return self.processors[processor_name]
    

    def get_processor_name(self, agent_name, account_name):
        processor_name = agent_name + '_' + account_name
        return processor_name