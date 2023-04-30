from message_processor import MessageProcessor, FileResponseHandler
from prompt_manager import PromptManager

def role_play(seed_conversation=[], context_type="semantic", language_code='en-US'):
    exit_words = ["adiós", "bye", "quit"]
    prompt_base_path = "data/prompts"

    language = language_code[:2]
    handler = FileResponseHandler()

    prompt_manager = PromptManager(prompt_base_path, "lucy", "test", language)
    processor = MessageProcessor(prompt_manager, handler, seed_conversation, context_type, language)

    while True:
        user_input = input(">> ")
        if user_input.lower() in exit_words:
            processor.save_conversations()
            break
        if user_input == "exit":
            return

        response = processor.process_message(user_input, "console")

        print(response)

lucy = [
    {"role": "system", "content": "You are Lucy, a super friendly and helpful AI assistant who can have a conversation and likes to ask questions. Remember to use the information in the prompt and background context when answering questions, including software engineering topics."}
]

role_play(seed_conversation=lucy, context_type='hybrid', language_code='en-US')
