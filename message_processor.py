import openai
import logging
from prompt_manager import PromptManager
from response_handler import ResponseHandler
from response_handler import FileResponseHandler
from api_helpers import ask_question

# Configure logging
logging.basicConfig(filename='my_log_file.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class MessageProcessor:
    def __init__(self, prompt_manager, handler, seed_conversations, context_type, language):
        #self.name = name
        self.language = language
        self.prompt_manager = prompt_manager
        self.seed_conversations = seed_conversations
        self.context_type = context_type
        self.handler = handler
        self.open_conversations()

    def process_message(self, message, conversationId="0"):
        logging.info(f'Processing message inbound: {message}')

        conversation = self.assemble_conversation(message, conversationId)

        logging.info(f'Processing message prompt: {conversation}')
        
        response = ask_question(conversation)
        response = self.handler.handle_response(response, 700)  # Use the handler instance
        logging.info(f'Processing message response: {response}')

        conversation = []
        conversation.append({"role": "user", "content": message})
        if not response.startswith("Response is too long"):
            conversation.append({"role": "system", "content": response})

        self.prompt_manager.store_prompt_conversations(conversation, conversationId)

        return response

    def save_conversations(self):
        self.prompt_manager.save()

    def open_conversations(self):
        try:
            self.prompt_manager.load()
        except FileNotFoundError:
            print('The file does not exist.')



    def assemble_conversation(self, content_text, conversationId, max_prompt_chars=4000, max_prompt_conversations=20):
        logging.info(f'assemble_conversation: {self.context_type}')
        my_content = [{"role": "user", "content": content_text}]

        if self.context_type == "keyword":
            matched_elements = self.prompt_manager.get_conversations(content_text)
        elif self.context_type == "semantic":
            matched_elements = self.prompt_manager.find_closest_conversation(content_text,8,0.1)
        elif self.context_type == "hybrid":
            matched_elements = self.prompt_manager.find_closest_conversation(content_text,8,0.1)
            matched_elements = matched_elements + self.prompt_manager.find_latest_conversation(2)
        elif self.context_type == "latest":
            matched_elements = self.prompt_manager.find_latest_conversation(3)
        else:
            matched_elements = []

        logging.info(f'Processing matched_elements: {matched_elements}')

        if len(matched_elements) > 0:
            sorted_matched_elements = sorted(matched_elements, key=lambda x: x["utc_timestamp"])
            matched_conversations = [conv_dict for conv_dict in sorted_matched_elements]
            all_text = " - ".join([conv["content"] for conv in matched_conversations])
            all_text = f"you previously discussed: {all_text}"
            new_conversation_element = {"role": "system", "content": all_text}
            matched_conversations = [new_conversation_element]
            conversations = self.seed_conversations + matched_conversations + my_content
        else:
            conversations = self.seed_conversations + my_content

        total_chars = sum(len(conv["content"]) for conv in conversations)
        total_conversations = len(conversations)

        logging.info(f'Processing matched_elements 2: {conversations}')

        if total_chars > max_prompt_chars:
            truncated_conversations = self.seed_conversations.copy()
            total_chars = sum(len(conv["content"]) for conv in truncated_conversations)
            for conv in matched_conversations + my_content:
                if total_chars + len(conv["content"]) <= max_prompt_chars:
                    truncated_conversations.append(conv)
                    total_chars += len(conv["content"])
                else:
                    break
            conversations = truncated_conversations
            logging.info(f'Processing matched_elements 3: {conversations}')
        elif total_conversations > max_prompt_conversations:
            remaining_space = max_prompt_conversations - len(self.seed_conversations) - 1
            conversations = self.seed_conversations + matched_conversations[-remaining_space:] + my_content
            logging.info(f'Processing matched_elements 4: {conversations}')

        logging.info(f'returned prompt: {conversations}')
        return conversations
