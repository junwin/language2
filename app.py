from flask import Flask, request, jsonify, send_from_directory
from flask_swagger_ui import get_swaggerui_blueprint
from message_processor_store import MessageProcessorStore
from response_handler import FileResponseHandler
from prompt_manager import PromptManager
from prompt_store import PromptStore
from agent_manager import AgentManager
from preset_prompts import PresetPrompts


from flask_cors import CORS
import ssl
import json
from typing import Set
import logging

from injector import Injector


from container_config import container
from config_manager import ConfigManager
from message_processor_store import MessageProcessorStore



app = Flask(__name__)
CORS(app)


config = ConfigManager('config.json')


# Set up Swagger UI
SWAGGER_URL = '/api/docs'
API_URL = '/static/swagger.json'

# things that should go in a config file
prompt_base_path = config.get("prompt_base_path", "data/prompts")
agents_path = config.get("agents_path", "static/data/agents.json")
preset_path = config.get("preset_path", "static/data/presets.json")



# Configure logging
logging.basicConfig(filename='logs/my_log_file.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


swaggerui_blueprint = get_swaggerui_blueprint(
    config.get("swagger_url", "/api/docs"),
    config.get("api_url", "/static/swagger.json"),
    config={
        'app_name': config.get("app_name", "Lucy API")
    }
)
app.register_blueprint(swaggerui_blueprint, url_prefix=config.get("swagger_url", "/api/docs"))


message_processor_store = MessageProcessorStore()



handler = FileResponseHandler(config.get("account_output_path"), 1000)

# Get the AgentManager instance
agent_manager = container.get(AgentManager)
agent_manager.load_agents()


# Get the Prompts instance
preset_prompts = container.get(PresetPrompts)
preset_prompts.load()




def get_prompt_manager(prompt_base_path, agent_name, account_name, language_code):
    prompt_store = container.get(PromptStore)
    return prompt_store.get_prompt_manager(agent_name, account_name, language_code)
   

def get_message_processor(agent_name, account_name):
    manager=message_processor_store.get_message_processor(agent_name, account_name)
    return manager


@app.route('/ask', methods=['POST'])
def ask():
    question = request.json.get('question', '')
    agentName = request.json.get('agentName', '')
    agentName = agentName.lower()
    accountName = request.json.get('accountName', '')
    accountName = accountName.lower()
    select_type = request.json.get('selectType', '')
    conversationId = request.json.get('conversationId', '')

    if not question or not agentName or not accountName:
        return jsonify({"error": "Missing question, agentName, accountName, or conversationId"}), 400


    if not agent_manager.is_valid(agentName):
        return jsonify({"error": "Invalid agentName"}), 400

    my_agent = agent_manager.get_agent(agentName)
    
    processor_name = get_processor_name(agentName, accountName)
    file_path = get_complete_path(prompt_base_path, agentName, accountName)
    if not select_type:
        select_type = my_agent['select_type']
    agents = agent_manager.get_available_agents()
    processor = get_message_processor(agentName, accountName)

    processor.context_type = select_type
    # Modify the process_message method in the MessageProcessor class if needed
    response = processor.process_message(question, conversationId)
    # processor.save_conversations()
    return jsonify({"response": response})


@app.route('/agents', methods=['GET'])
def get_agents():
    try: 
        my_list = agent_manager.get_available_agents()
        zz = jsonify(my_list)
        return jsonify(my_list)
    except Exception as e:
            # log the exception or print the error message
            print(f"An error occurred: {e}")
    return []
   


@app.route('/computeConversations', methods=['POST'])
def post_prompt():

    question = request.json.get('query', '')
    agentName = request.json.get('agentName', '')
    agentName = agentName.lower()
    accountName = request.json.get('accountName', '')
    accountName = accountName.lower()
    select_type = request.json.get('selectType', '')
    conversationId = request.json.get('conversationId', '')

    if not question or not agentName or not accountName:
        return jsonify({"error": "Missing question, agentName, accountName, or conversationId"}), 400

    if not agent_manager.is_valid(agentName):
        return jsonify({"error": "Invalid agentName"}), 400

    my_agent = agent_manager.get_agent(agentName)


    if not select_type:
        select_type = my_agent['select_type']

    agents = agent_manager.get_available_agents()

    processor = get_message_processor(prompt_base_path, agentName, accountName, agents, processors)

    processor.context_type = select_type

    prompt = processor.assemble_conversation( question, conversationId, my_agent, select_type)

    return jsonify(prompt)


@app.route('/prompts', methods=['POST'])
def post_prompts():
    agentName = request.json.get('agentName', '').lower()
    accountName = request.json.get('accountName', '').lower()
    conversationId = request.json.get('conversationId', '')
    prompt = request.get_json()

    if not agentName or not accountName or not conversationId:
        return jsonify({"error": "Missing agentName, accountName, conversationId"}), 400

    if not agent_manager.is_valid(agentName):
        return jsonify({"error": "Invalid agentName"}), 400

    agent = agent_manager.get_agent(agentName)

    prompt_manager = get_prompt_manager( prompt_base_path, agentName, accountName, agent['language_code'][:2])

    # add the new prompt to the prompt manager check the bool success to see if it was added
    success = prompt_manager.store_prompt(prompt)

    if not success:
        return jsonify({"error": "Failed to store the new prompt"}), 400

    # Save the new prompt
    prompt_manager.save()

    # Return the newly created prompt
    return jsonify(prompt)


@app.route('/prompts', methods=['PUT'])
def put_prompts():
    agentName = request.args.get('agentName', '').lower()
    accountName = request.args.get('accountName', '').lower()
    prompt_id = request.args.get('id', '')
    data = request.get_json()

    # json_string = request.get_data(as_text=True)
    # data2 = json.loads(json_string)

    if not agentName or not accountName or not prompt_id or not data:
        return jsonify({"error": "Missing agentName, accountName, or data"}), 400

    if not agent_manager.is_valid(agentName):
        return jsonify({"error": "Invalid agentName"}), 400

    agent = agent_manager.get_agent(agentName)

    prompt_manager = get_prompt_manager( prompt_base_path, agentName, accountName, agent['language_code'][:2])

    success = prompt_manager.update_prompt(prompt_id, data)
    if success:
        prompt_manager.save()
        return jsonify(data)

    return jsonify({"status": "fail", "message": "Prompt failed to update"})


@app.route('/prompts', methods=['DELETE'])
def delete_prompts():
    agentName = request.args.get('agentName', '').lower()
    accountName = request.args.get('accountName', '').lower()
    prompt_id = request.args.get('id', '')

    if not agentName or not accountName or not prompt_id:
        return jsonify({"error": "Missing agentName, accountName, or id"}), 400

    if not agent_manager.is_valid(agentName):
        return jsonify({"error": "Invalid agentName"}), 400

    agent = agent_manager.get_agent(agentName)

    prompt_manager = get_prompt_manager(prompt_base_path, agentName, accountName, agent['language_code'][:2])

    success = prompt_manager.delete_prompt(prompt_id)
    if success:
        prompt_manager.save()
        return jsonify({"status": "success", "message": "Prompt successfully deleted"})

    return jsonify({"status": "fail", "message": "Prompt failed to deleted"})


@app.route('/prompts', methods=['GET'])
def get_prompts():
    agentName = request.args.get('agentName', '').lower()
    accountName = request.args.get('accountName', '').lower()
    conversationId = request.args.get('conversationId', '')

    if not agentName or not accountName or not conversationId:
        return jsonify({"error": "Missing agentName, accountName, or conversationId"}), 400

    if not agent_manager.is_valid(agentName):
        return jsonify({"error": "Invalid agentName"}), 400

    agent = agent_manager.get_agent(agentName)

    prompt_manager = get_prompt_manager(prompt_base_path, agentName, accountName, agent['language_code'][:2])

    prompts = prompt_manager.get_prompts(conversationId)

    return jsonify(prompts)


@app.route('/conversationIds', methods=['GET'])
def get_conversation_ids():
    agentName = request.args.get('agentName', '').lower()
    accountName = request.args.get('accountName', '').lower()

    if not agentName or not accountName:
        return jsonify({"error": "Missing agentName or accountName"}), 400

    if not agent_manager.is_valid(agentName):
        return jsonify({"error": "Invalid agentName"}), 400

    agent = agent_manager.get_agent(agentName)

    prompt_manager = get_prompt_manager( prompt_base_path, agentName, accountName, agent['language_code'][:2])
    # prompt_manager.load()
    conversation_ids = prompt_manager.get_distinct_conversation_ids()
    return jsonify(conversation_ids)


@app.route('/conversationIds', methods=['PUT'])
def change_conversation_id():
    agentName = request.args.get('agentName', '').lower()
    accountName = request.args.get('accountName', '').lower()
    existingId = request.args.get('existingId', '')
    newId = request.args.get('newId', '')

    if not agentName or not accountName or not existingId or not newId:
        return jsonify({"error": "Missing agentName, accountName, existingId, or newId"}), 400
    
    if not agent_manager.is_valid(agentName):
        return jsonify({"error": "Invalid agentName"}), 400

    agent = agent_manager.get_agent(agentName)

    prompt_manager = get_prompt_manager(prompt_base_path, agentName, accountName, agent['language_code'][:2])
    prompt_manager.load()
    prompt_manager.change_conversation_id(existingId, newId)
    prompt_manager.save()
    return jsonify({"message": "Conversation ID changed successfully"})


def get_complete_path(base_path, agent_name, account_name):
    full_path = base_path + '/' + agent_name + '_' + account_name
    return full_path


def get_processor_name(agent_name, account_name):
    processor_name = agent_name + '_' + account_name
    return processor_name



if __name__ == "__main__":
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(config.get("ssl_cert", "192.168.1.245.pem"), config.get("ssl_key", "192.168.1.245-key.pem"))
    app.run(host=config.get("host", "0.0.0.0"), port=config.get("port", 5000), ssl_context=context, debug=config.get("debug", True))