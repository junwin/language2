import openai
import logging
from prompt_store import PromptStore
from prompt_manager import PromptManager

from response_handler import FileResponseHandler
from source_code_response_handler import SourceCodeResponseHandler
from agent_manager import AgentManager
from message_preProcess import MessagePreProcess
from preset_handler import PresetHandler
from api_helpers import ask_question, get_completion
from preset_prompts import PresetPrompts
import re
from injector import Injector
from container_config import container
from config_manager import ConfigManager   
 



class MessageProcessor:
    def __init__(self, agent_name: str, account_name :str ):
        # self.name = name
        agent_manager = container.get(AgentManager)
        self.agent = agent_manager.get_agent(agent_name)
        self.config = container.get(ConfigManager) 
        prompt_base_path=self.config.get('prompt_base_path')  
        prompt_store = container.get(PromptStore)
        self.account_prompt_manager: PromptManager = prompt_store.get_prompt_manager(self.agent['name'], account_name, self.agent['language_code'][:2])
        self.agent_prompt_manager: PromptManager = prompt_store.get_prompt_manager(self.agent['name'], self.config.get("agent_internal_account_name"), self.agent['language_code'][:2])   
         
        self.seed_conversations = []
        self.context_type = self.agent["select_type"]
        self.handler = container.get(FileResponseHandler)   
        self.preprocessor = container.get(MessagePreProcess)
        self.account_name = account_name
        self.preset_handler = PresetHandler(container.get(PresetPrompts))



  

    

    def process_message(self, message, conversationId="0"):
        logging.info(f'Processing message inbound: {message}')
        agent_manager = container.get(AgentManager)
        agent = agent_manager.get_agent(self.agent_prompt_manager.agent_name)
        model = agent["model"]
        temperature = agent["temperature"]

        # Check for alternative processing
        myResult = self.preprocessor.alternative_processing(message, conversationId, agent, self.account_prompt_manager)

        if myResult["action"] == "return":
            return myResult["result"]
        if myResult["action"] == "storereturn":
            self.add_response_message(conversationId,  message, myResult["result"])
            return myResult["result"]
        elif myResult["action"] == "continue":
             message = myResult["result"]
        elif myResult["action"] == "swapseed":
             seed_info = myResult["result"]
             seed_name=seed_info["seedName"]
             seed_paramters=seed_info["values"]

        conversation = self.assemble_conversation(message,conversationId,  agent, self.context_type)
       

        logging.info(f'Processing message prompt: {conversation}')

        response = ask_question(conversation, model, temperature)

        if 'source_code' in response and 'file_path' in response:
            logging.info(f'Processing code response: {response}')
            my_handler = SourceCodeResponseHandler(self.config.get('account_output_path'), 0)
            response = my_handler.handle_response(self.account_name, response)  # Use the source code handler instance
        else:
            response = self.handler.handle_response(self.account_name, response)  # Use the handler instance
            

        logging.info(f'Processing message response: {response}')

        if self.config.get('save_reposnses') == 'true':
            self.add_response_message(conversationId,  message, response)
            self.account_prompt_manager.save()

        logging.info(f'Processing message complete: {message}')

        return response
    
    def is_none_or_empty(self, string):
        return string is None or string.strip() == ""

    def add_response_message(self, conversationId, request: str, response: str):
        conversation = []
        if request is not self.is_none_or_empty(request):
            conversation.append({"role": "user", "content": request})
        if not response.startswith("Response is too long"):
            conversation.append({"role": "assistant", "content": response})

        self.account_prompt_manager.store_prompt_conversations(conversation, conversationId)


    

    def remove_utc_timestamp(self, data):
        new_data = []
        for item in data:
            new_item = {"role": item["role"], "content": item["content"]}
            new_data.append(new_item)
        return new_data
    
   
    
    def get_data_item(self, input_string, data_point):
        regex_pattern = f"{re.escape(data_point)}\\s*(.*)"
        result = re.search(regex_pattern, input_string)
        if result:
            return result.group(1).strip()
        else:
            return None

    
    def assemble_conversation(self, content_text, conversationId, agent, context_type="none", seed_name="seed", seed_paramters=[], max_prompt_chars=6000, max_prompt_conversations=20):
        logging.info(f'assemble_conversation_new: {context_type}')


        # agent properties that are used with the completions API
        model = agent["model"]
        temperature = agent["temperature"]
        num_past_conversations = agent["num_past_conversations"]
        num_relevant_conversations = agent["num_relevant_conversations"]
        use_prompt_reduction = agent["use_prompt_reduction"]

        my_user_content = self.account_prompt_manager.create_conversation_item(content_text, 'user') 


        # get the agents seed prompts - this is fixed information for the agent
        agent_matched_seed_ids = self.get_matched_ids(self.agent_prompt_manager, "keyword_match_all", seed_name, num_relevant_conversations, num_past_conversations)
        agent_matched_ids = self.get_matched_ids(self.agent_prompt_manager, "keyword", content_text, num_relevant_conversations, num_past_conversations)
        agent_all_matched_ids = agent_matched_seed_ids + agent_matched_ids
        matched_conversations_agent = self.agent_prompt_manager.get_conversations_ids(agent_all_matched_ids)
        if context_type == "simpleprompt":
            my_agent_prompt = self.agent_prompt_manager.get_conversations_ids(agent_matched_ids)
            my_text = my_agent_prompt[0]["content"] 
            content_text = my_text + content_text   
            matched_conversations_agent = []
            #my_text = self.agent_prompt_manager.get_conversation_text_by_id(my_agent_prompt[0]) 


        my_user_content = self.account_prompt_manager.create_conversation_item(content_text, 'user') 

        # get any matched account prompts for the account - this is fixed information for the account
        account_matched_ids = self.get_matched_ids(self.account_prompt_manager, context_type, content_text, num_relevant_conversations, num_past_conversations)
        matched_conversations_account = self.account_prompt_manager.get_conversations_ids(account_matched_ids)

        # does this agent use an open ai model to reduce and select only relevant prompts
        if use_prompt_reduction:
            text_info = self.account_prompt_manager.get_formatted_dialog(account_matched_ids)

            preset_values = [text_info, content_text]
            my_useful_response = self.preset_handler.process_preset_prompt_values("getrelevantfacts", preset_values)
            useful_reponse = self.get_data_item(my_useful_response, "Useful information:")

            if useful_reponse != 'NONE' :
                matched_conversations_account = self.account_prompt_manager.create_conversation_item(useful_reponse, 'assistant') 
            else:
                matched_conversations_account = []


        full_prompt = matched_conversations_agent + matched_conversations_account  + my_user_content

        #logging.info(f'returned prompt: {full_prompt}')
        return full_prompt

    def get_matched_ids(self, prompt_manager: PromptManager, context_type : str, content_text : str, num_relevant_conversations : int, num_past_conversations : int):
        matched_accountIds = []

        if context_type == "keyword":
            matched_accountIds = prompt_manager.find_keyword_promptIds(content_text, False, num_relevant_conversations)
        elif context_type == "keyword_match_all":
            matched_accountIds = prompt_manager.find_keyword_promptIds(content_text, True, num_relevant_conversations)
        elif context_type == "semantic":
            matched_accountIds = prompt_manager.find_closest_promptIds(content_text, num_relevant_conversations, 0.1)
        elif context_type == "hybrid":
            matched_prompts_closest = prompt_manager.find_closest_promptIds(content_text, num_relevant_conversations, 0.1)
            matched_prompts_latest = prompt_manager.find_latest_promptIds(num_past_conversations)
            matched_accountIds = matched_prompts_closest + matched_prompts_latest
        elif context_type == "latest":
            matched_accountIds = prompt_manager.find_latest_promptIds(num_past_conversations)
        else:
            matched_accountIds = []

        # sort the account prompts
        distinct_list = list(set(matched_accountIds))
        sorted_list = sorted(distinct_list)

        return sorted_list

        

    
