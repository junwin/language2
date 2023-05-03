from flask import Flask, request, jsonify, send_from_directory
from flask_swagger_ui import get_swaggerui_blueprint
from message_processor import MessageProcessor, FileResponseHandler
from prompt_manager import PromptManager
from flask_cors import CORS
import ssl
import json
from typing import Set


class Agent:
    def __init__(self, seed_conversation, language_code, select_type, max_output_size):
        self.seed_conversation = seed_conversation
        self.language_code = language_code
        self.select_type = select_type
        self.max_output_size = max_output_size

app = Flask(__name__)
CORS(app)

# Set up Swagger UI
SWAGGER_URL = '/api/docs'
API_URL = '/static/swagger.json'

prompt_base_path = "data/prompts"

swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={
        'app_name': "Lucy API"
    }
)
app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)

agents = {
    "lucy": Agent(
        seed_conversation=[],
        language_code='en-US',
        select_type='hybrid',
        max_output_size=750

    ),
    "maria": Agent(
        seed_conversation=[],
        language_code='es-US',
        select_type='latest',
        max_output_size=1000
    ),
    "pedro": Agent(
        seed_conversation=[],
        language_code='es-US',
        select_type='latest',
        max_output_size=1000
    ),
    "glinda": Agent(
        seed_conversation=[],
        language_code='en-US',
        select_type='hybrid',
        max_output_size=4000
    ),
        "dorothy": Agent(
        seed_conversation=[],
        language_code='en-US',
        select_type='keyword',
        max_output_size=4000
    ),
 
}


processors = {}

handler = FileResponseHandler()


prompt_managers = {}

def get_prompt_manager(prompt_base_path, agent_name, account_name, language_code):
    key = agent_name + account_name
    if key not in prompt_managers:
        prompt_manager = PromptManager(prompt_base_path, agent_name, account_name, language_code[:2])
        prompt_manager.load()
        prompt_managers[key] = prompt_manager
    return prompt_managers[key]

def get_message_processor(prompt_base_path, agent_name, account_name, agents, processors):
    processor_name = get_processor_name(agent_name, account_name)
    
    if processor_name not in processors:
        agent = agents[agent_name]
        my_handler = FileResponseHandler(agent.max_output_size)
        account_prompt_manager = get_prompt_manager(prompt_base_path, agent_name, account_name, agent.language_code[:2])
        agent_prompt_manager = get_prompt_manager(prompt_base_path, agent_name, "aaaa", agent.language_code[:2])
        proc = MessageProcessor(agent_prompt_manager, account_prompt_manager, my_handler, agent.select_type)
        processors[processor_name] = proc
    
    return processors[processor_name]



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

    if agentName not in agents:
        return jsonify({"error": "Invalid agentName"}), 400

    my_agent = agents[agentName]
    processor_name = get_processor_name(agentName, accountName)
    file_path = get_complete_path(prompt_base_path, agentName, accountName)
    if not select_type:
        select_type = my_agent.select_type

    processor = get_message_processor(prompt_base_path, agentName, accountName, agents, processors)

  

    processor.context_type = select_type
    response = processor.process_message(question, conversationId)  # Modify the process_message method in the MessageProcessor class if needed
    #processor.save_conversations()
    return jsonify({"response": response})


@app.route('/agents', methods=['GET'])
def get_agents():
    # transform the agents dictionary into the output format
    agents_list = [
        {
            "agentName": agent_name,
            "seed_conversation": agent.seed_conversation,
            "language_code": agent.language_code,
            "select_type": agent.select_type
        }
        for agent_name, agent in agents.items()
    ]
    return jsonify(agents_list)



@app.route('/computeConversations', methods=['POST'])
def post_prompt():
    agentName = request.json.get('agentName', '').lower()
    accountName = request.json.get('accountName', '').lower()
    selectType = request.json.get('selectType', '').lower() # this will override the selectType in the agent
    query = request.json.get('query', '')
    conversationId = request.json.get('conversationId', '')

    if not agentName or not accountName or not query:
        return jsonify({"error": "Missing agentName, accountName, or query"}), 400

    if agentName not in agents:
        return jsonify({"error": "Invalid agentName"}), 400

    processor_name = get_processor_name(agentName, accountName)
    file_path = get_complete_path(prompt_base_path, agentName, accountName)

    
    
    processor = get_message_processor(prompt_base_path, agentName, accountName, agents, processors)

    processor.context_type = selectType
    prompt = processor.assemble_conversation(query, conversationId, max_prompt_chars=4000, max_prompt_conversations=20)

    # Modify the following line to generate the desired prompt based on the provided information
    # prompt = [{"role": "system", "content": "you previously discussed: How do you log to a file in javascript"}]

    return jsonify(prompt)

@app.route('/prompts', methods=['POST'])
def post_prompts():
    agentName = request.json.get('agentName', '').lower()
    accountName = request.json.get('accountName', '').lower()
    conversationId = request.json.get('conversationId', '')
    prompt = request.get_json()

    if not agentName or not accountName or not conversationId:
        return jsonify({"error": "Missing agentName, accountName, conversationId"}), 400

    if agentName not in agents:
        return jsonify({"error": "Invalid agentName"}), 400

    agent = agents[agentName]

    prompt_manager = get_prompt_manager(prompt_base_path, agentName, accountName, agent.language_code[:2])

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

    #json_string = request.get_data(as_text=True)
    #data2 = json.loads(json_string)

    if not agentName or not accountName or not prompt_id or not data:
        return jsonify({"error": "Missing agentName, accountName, or data"}), 400

    if agentName not in agents:
        return jsonify({"error": "Invalid agentName"}), 400

    agent = agents[agentName]


    prompt_manager = get_prompt_manager(prompt_base_path, agentName, accountName, agent.language_code[:2])

    success = prompt_manager.update_prompt(prompt_id, data)
    if success:
        prompt_manager.save()
        return jsonify(data)

    return jsonify({"status": "fail", "message": "Prompt failed to update"})


@app.route('/prompts', methods=['DELETE'])
def delete_prompts():
    agentName = request.args.get('agentName', '').lower()
    accountName = request.args.get('accountName', '').lower()
    prompt_id = request.args.get('id','')

    if not agentName or not accountName or not prompt_id:
        return jsonify({"error": "Missing agentName, accountName, or id"}), 400

    if agentName not in agents:
        return jsonify({"error": "Invalid agentName"}), 400

    agent = agents[agentName]
      
    prompt_manager = get_prompt_manager(prompt_base_path, agentName, accountName, agent.language_code[:2])

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

    if agentName not in agents:
        return jsonify({"error": "Invalid agentName"}), 400

    agent = agents[agentName]
      
    prompt_manager = get_prompt_manager(prompt_base_path, agentName, accountName, agent.language_code[:2])

    prompts = prompt_manager.get_prompts(conversationId)

    return jsonify(prompts)


@app.route('/conversationIds', methods=['GET'])
def get_conversation_ids():
    agentName = request.args.get('agentName', '').lower()
    accountName = request.args.get('accountName', '').lower()

    if not agentName or not accountName:
        return jsonify({"error": "Missing agentName or accountName"}), 400

    if agentName not in agents:
        return jsonify({"error": "Invalid agentName"}), 400

    agent = agents[agentName]

    prompt_manager = get_prompt_manager(prompt_base_path, agentName, accountName, agent.language_code[:2])
    prompt_manager.load()
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

    if agentName not in agents:
        return jsonify({"error": "Invalid agentName"}), 400

    agent = agents[agentName]

    prompt_manager = get_prompt_manager(prompt_base_path, agentName, accountName, agent.language_code[:2])
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
    context.load_cert_chain('192.168.1.245.pem', '192.168.1.245-key.pem')
    app.run(host='0.0.0.0', port=5000, ssl_context=context, debug=True)


