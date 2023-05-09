import openai
import logging
from prompt_manager import PromptManager
from response_handler import ResponseHandler
from response_handler import FileResponseHandler
from agent_manager import AgentManager
from api_helpers import ask_question, get_completion
from prompts import Prompts
import re
from typing import List, Dict, Set
import json
import logging

class MessagePreProcess:
    def alternative_processing(self, message, conversationId, agent, account_prompt_manager):
        response = {"action": None, "result": None}
        
        if message == "please summarize":
            myResult = self.process_summarize_request(message, conversationId, account_prompt_manager)
            response["action"] = "return"
            response["result"] = myResult
        elif message.startswith("glinda"):
            myResult = self.process_glinda_request(message, conversationId, agent, account_prompt_manager)
            response["action"] = "continue"
            response["result"] = myResult
        elif message.startswith("/"):
            response["action"] = "return"
            response["result"] = self.process_preset_prompt(message)
 
        return response
    
    def process_preset_prompt(self, message)  -> str: 
        myResult = self.transform_to_dict(message, 1)
        preset_name = myResult["seedName"]
        prompt = Prompts.instance().get_prompt(preset_name)
        if prompt is None:
            my_response = "no such preset: " + preset_name
            return my_response

        num_mandatory_params = prompt['num_mandatory_params']
        myResult = self.transform_to_dict(message, num_mandatory_params)

        values = myResult["values"]
        preset_name = myResult["seedName"]

        if preset_name == "eft_data_chunker":
            response = self.etf_chunker(message)
            return response
        
        return self.process_preset_prompt_values(preset_name, values)
    
    def process_preset_prompt_values(self, preset_name: str, values: List[str])  -> str: 
        prompt = Prompts.instance().get_prompt(preset_name)
        
        if prompt is None:
            my_response = "no such preset: " + preset_name
            return my_response
        
        num_mandatory_params = prompt["num_mandatory_params"]
        my_promp_text = prompt["prompt"]
        if "model" in prompt:
            model = prompt["model"]
        else:   
            model = self.infer_model(preset_name)

        if len(values) < num_mandatory_params:
            my_response = "missing some parameters here is some info: " + prompt["info"]
        else:
            prompt = self.substitute_params(values, my_promp_text)
            my_response = get_completion(prompt, 0, model)

        return my_response
    
    def infer_model(self, message: str) -> str:
        model = "gpt-4"
        if message.startswith("gpt-3.5-turbo"):
            model = "gpt-3.5-turbo"
        if message.startswith("gpt-3.5"):
            model = "gpt-3.5-turbo"
        return model

    def transform_to_dict(self, input_string, num_parms=0, delimiter=','):
        if num_parms < 0:
            raise ValueError("num_parms must be a non-negative integer.")
            
        input_list = input_string.strip().split(delimiter, num_parms)
        seed_name = input_list[0].lstrip('/')
        values_list = [value.strip() for value in input_list[1:]]
        
        if num_parms > 0 and len(values_list) > num_parms - 1:
            last_value = delimiter.join(values_list[num_parms-1:])
            values_list = values_list[:num_parms-1] + [last_value]

        return {"seedName": seed_name, "values": values_list}
        
    def substitute_params(self, values, input_text):
        for i in range(len(values)):
            param_name = f"#<P{i+1}>"
            param_value = values[i]
            input_text = input_text.replace(param_name, param_value)
        return input_text

    def process_summarize_request(self, message, conversationId, account_prompt_manager):
        my_text = account_prompt_manager.get_conversation_text_by_id(conversationId)
        my_request = "please summarize this: " + my_text

        response = get_completion(my_request, 0, "gpt-3.5-turbo")

        return "return", response
    
    def process_glinda_request(self, message, conversationId, agent, account_prompt_manager):
        my_text = account_prompt_manager.get_conversation_text_by_id(conversationId)
        my_request = "given we use the lifecoachschool method - please analyse the following request from the user look for feelings and circumstances " + my_text

        conversation = self.assemble_conversation(my_request, conversationId, "keyword")
 
        # logging.info(f'process_glinda_request: {conversation}')
        response = ask_question(conversation, agent["model"], agent["temperature"])
        # logging.info(f'process_glinda_request: {message}')

        new_request = "given that: " + response + " the user original request is: " + message

        logging.info(f'process_glinda_request result: {new_request}')

        #self.add_response_message(conversationId,  message, response)

        return "continue", new_request
    
    def etf_chunker(self, message)  -> str: 

        # this just gets to the prompt name - we dont know how many parameters there are
        myResult = self.transform_to_dict(message, 1)
        preset_name = myResult["seedName"]
        

        prompt = Prompts.instance().get_prompt(preset_name)
        num_mandatory_params =  prompt['num_mandatory_params']
        myResult = self.transform_to_dict(message, num_mandatory_params)
        values = myResult["values"]

        num_mandatory_params =  prompt['num_mandatory_params']

        my_len = len(values)

        if my_len < num_mandatory_params:
            response = "missing some parameters here is some info: " + prompt["info"]
            return response

        file_path = values[0]
        chunk_size = int(values[1])
        preset_name_chunk = values[2]
        preset_name_analysis = values[3]
        if my_len > 4:
            analysis_instructions = values[4]
        else:
            analysis_instructions = ""

        response = self.process_json_chunks(file_path, chunk_size, preset_name_chunk, preset_name_analysis, analysis_instructions)

        return response

    def read_chunks(self, data, chunk_size):
        for i in range(0, len(data), chunk_size):
            yield data[i:i + chunk_size]

    def process_json_chunks(self, file_path, chunk_size, preset_name_chunk, preset_name_analysis, analysis_instructions=''):
        logging.info(f'process_json_chunks: start')

        with open(file_path, 'r') as file:
            data = json.load(file)

        digest = ""
        chunks = self.read_chunks(data, chunk_size)

        count = 0
        for chunk in chunks:
            chunk_str = json.dumps(chunk)
            summary = self.process_preset_prompt_values(preset_name_chunk, [chunk_str])
            digest += summary
            print(f'chunk processed: {count}')
            count += 1
        print('all chunks processed')
        print('starting analysis')
        logging.info(f'digest: {digest}')
        analysis = self.process_preset_prompt_values(preset_name_analysis, [digest, analysis_instructions])
        print('done')
        logging.info(f'analysis: {analysis}')
        logging.info(f'process_json_chunks: end')
        return analysis

