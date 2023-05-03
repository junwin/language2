import openai
import logging
from prompt_manager import PromptManager
from response_handler import ResponseHandler
from response_handler import FileResponseHandler
from api_helpers import ask_question

# Configure logging
logging.basicConfig(filename='my_log_file.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


class MessageProcessor:
    def __init__(self, agent_prompt_manager, account_prompt_manager, handler, context_type):
        # self.name = name
        self.agent_prompt_manager = agent_prompt_manager
        self.account_prompt_manager = account_prompt_manager
        self.seed_conversations = []
        self.context_type = context_type
        self.handler = handler
        # self.open_conversations()

    def process_message(self, message, conversationId="0"):
        logging.info(f'Processing message inbound: {message}')

        # Check for alternative processing
        action, response = self.alternative_processing(message, conversationId)
        if action == "return":
            return response
        elif action == "continue":
             message = response

        # Normal default process
        conversation = self.assemble_conversation(message, conversationId, self.context_type)
        logging.info(f'Processing message prompt: {conversation}')

        response = ask_question(conversation)
        response = self.handler.handle_response(response, 700)  # Use the handler instance
        logging.info(f'Processing message response: {response}')

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
            conversation.append({"role": "system", "content": response})

        self.account_prompt_manager.store_prompt_conversations(conversation, conversationId)


    def alternative_processing(self, message, conversationId):
        if message == "please summarize":
            return self.process_summarize_request(message, conversationId)
        if message.startswith("glinda"):
            return self.process_glinda_request(message, conversationId)

        return None, None

    def process_summarize_request(self, message, conversationId):
        my_text = self.account_prompt_manager.get_conversation_text_by_id(conversationId)
        my_request = "please summarize this: " + my_text

        conversation = self.assemble_conversation(my_request, conversationId, "none")
 
        logging.info(f'process_summarize_request: {conversation}')
        response = ask_question(conversation)
        logging.info(f'process_summarize_request: {message}')

        #self.add_response_message(conversationId,  message, response)

        return "return", response
    
    def process_glinda_request(self, message, conversationId):
        my_text = self.account_prompt_manager.get_conversation_text_by_id(conversationId)
        my_request = "given we use the lifecoachschool method - please analyse the following request from the user look for feelings and circumstances " + my_text

        conversation = self.assemble_conversation(my_request, conversationId, "keyword")
 
        logging.info(f'process_glinda_request: {conversation}')
        response = ask_question(conversation)
        logging.info(f'process_glinda_request: {message}')

        new_request = "given that: " + response + " the user original request is: " + message

        logging.info(f'process_glinda_request result: {new_request}')

        #self.add_response_message(conversationId,  message, response)

        return "continue", new_request


    def remove_utc_timestamp(self, data):
        new_data = []
        for item in data:
            new_item = {"role": item["role"], "content": item["content"]}
            new_data.append(new_item)
        return new_data

    def assemble_conversation(self, content_text, conversationId, context_type="none", max_prompt_chars=6000, max_prompt_conversations=20):
        logging.info(f'assemble_conversation: {context_type}')
        my_content = [{"role": "user", "content": content_text}]

        # get the agents seed prompts
        agent_ids = self.agent_prompt_manager.find_keyword_promptIds("seed")

        # get any matched prompts for the agent - this is fixed information for the agent
        matched_prompts_agent = self.agent_prompt_manager.find_closest_promptIds(
            content_text, 8, 0.1)
        matched_conversations_agent = self.agent_prompt_manager.get_conversations_ids(
            agent_ids + matched_prompts_agent)

        # get the account prompts that match the request or are the latest
        accountIds = []

        if context_type == "keyword":
            accountIds = self.account_prompt_manager.find_keyword_promptIds(
                content_text)
        elif context_type == "semantic":
            accountIds = self.account_prompt_manager.find_closest_promptIds(
                content_text, 8, 0.1)
        elif context_type == "hybrid":
            matched_prompts_closest = self.account_prompt_manager.find_closest_promptIds(
                content_text, 2, 0.1)
            matched_prompts_latest = self.account_prompt_manager.find_latest_promptIds(
                5)
            accountIds = matched_prompts_closest + matched_prompts_latest
        elif context_type == "latest":
            accountIds = self.account_prompt_manager.find_latest_promptIds(4)
        else:
            accountIds = []

        # sort the account prompts
        distinct_list = list(set(accountIds))
        sorted_list = sorted(distinct_list)

        # diagnositics
        for number in agent_ids:
            my_prompt = self.agent_prompt_manager.get_prompt(number)
            my_info = self.agent_prompt_manager.get_conversation_text(
                my_prompt)
            logging.info(f'DiagAgent: {my_info}')
            # print (my_info)

        for number in sorted_list:
            my_prompt = self.account_prompt_manager.get_prompt(number)
            my_info = self.account_prompt_manager.get_conversation_text(
                my_prompt)
            logging.info(f'DiagAccount: {my_info}')
            # print (my_info)

        # get the account conversations for the matched prompts ids
        matched_conversations_account = self.account_prompt_manager.get_conversations_ids(
            sorted_list)

        logging.info(
            f'Processing matched_elements: {matched_conversations_account}')

        if len(matched_conversations_account) > 0:
            # sorted_matched_elements = sorted(matched_elements, key=lambda x: x["utc_timestamp"])
            matched_conversations = [
                conv_dict for conv_dict in matched_conversations_account]
            all_text = " - ".join([conv["content"]
                                  for conv in matched_conversations])
            all_text = f"you previously discussed: {all_text}"
            new_conversation_element = {"role": "system", "content": all_text}
            matched_conversations = [new_conversation_element]
            conversations = matched_conversations_agent + matched_conversations + my_content
        else:
            conversations = matched_conversations_agent + my_content

        total_chars = sum(len(conv["content"]) for conv in conversations)
        total_conversations = len(conversations)

        logging.info(f'Processing matched_elements 2: {conversations}')

        if total_chars > max_prompt_chars:
            truncated_conversations = self.seed_conversations.copy()
            total_chars = sum(len(conv["content"])
                              for conv in truncated_conversations)
            for conv in matched_conversations_account + my_content:
                if total_chars + len(conv["content"]) <= max_prompt_chars:
                    truncated_conversations.append(conv)
                    total_chars += len(conv["content"])
                else:
                    break
            conversations = truncated_conversations
            logging.info(f'Processing matched_elements 3: {conversations}')
        elif total_conversations > max_prompt_conversations:
            remaining_space = max_prompt_conversations - \
                len(self.seed_conversations) - 1
            conversations = self.seed_conversations + \
                matched_conversations[-remaining_space:] + my_content
            logging.info(f'Processing matched_elements 4: {conversations}')

        logging.info(f'returned prompt: {conversations}')
        return conversations
