from message_processor import MessageProcessor, FileResponseHandler

def role_play(seed_conversation=[], file_name_root='out', context_type="semantic", language_code='en-US'):
    exit_words = ["adiós", "bye", "quit"]

    language = language_code[:2]
    handler = FileResponseHandler()

    processor = MessageProcessor(file_name_root, handler, seed_conversation, context_type, language)

    while True:
        user_input = input(">> ")
        if user_input.lower() in exit_words:
            processor.save_conversations()
            break
        if user_input == "exit":
            return

        response = processor.process_message(user_input)

        print(response)

lucy = [
    {"role": "system", "content": "You are Lucy, a super friendly and helpful AI assistant who can have a conversation and likes to ask questions. Remember to use the information in the prompt and background context when answering questions, including software engineering topics."}
]

role_play(seed_conversation=lucy, file_name_root='lucy', context_type='semantic', language_code='en-US')
