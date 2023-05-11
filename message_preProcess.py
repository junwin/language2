import logging
from prompt_manager import PromptManager
from response_handler import ResponseHandler
from response_handler import FileResponseHandler
from agent_manager import AgentManager
from api_helpers import ask_question, get_completion
from preset_prompts import PresetPrompts
import re
from typing import List, Dict, Set

import logging



from typing import List, Dict, Set
import re
from preset_handler import PresetHandler
from summarize_request_handler import SummarizeRequestHandler


class MessagePreProcess:

    def __init__(self, preset_prompts: PresetPrompts):
        self.preset_prompts = preset_prompts
        self.preset_handler = PresetHandler(self.preset_prompts)
        self.summarize_request_handler = SummarizeRequestHandler()

    def alternative_processing(self, message: str, conversationId : str, agent, account_prompt_manager: PromptManager):
        response = {"action": None, "result": None}
        
        if message == "please summarize":
            myResult = self.summarize_request_handler.process_summarize_request(message, conversationId, account_prompt_manager)
            response["action"] = "return"
            response["result"] = myResult
        elif message.startswith("/"):
            response["action"] = "return"
            response["result"] = self.preset_handler.process_preset_prompt(message, account_prompt_manager)
 
        return response
