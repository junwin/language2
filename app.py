from flask import Flask, request, jsonify, send_from_directory
from flask_swagger_ui import get_swaggerui_blueprint
from message_processor import MessageProcessor, FileResponseHandler
from prompt_manager import PromptManager
from flask_cors import CORS
import ssl
import json
from typing import Set


class Agent:
    def __init__(self, seed_conversation, language_code, select_type):
        self.seed_conversation = seed_conversation
        self.language_code = language_code
        self.select_type = select_type

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
        seed_conversation=[
            {"role": "system", "content": "You are Lucy, a super friendly and helpful AI assistant who can have a conversation and likes to ask questions. Remember to use the information in the prompt and background context when answering questions, including software engineering topics."}
        ],
        language_code='en-US',
        select_type='hybrid'
    ),
    "maria": Agent(
        seed_conversation=[
            {"role": "system", "content": "You are a super friendly and helpful AI spanish teacher called Maria and like to teach beginers spanish with conversation, role play and find out about your students and things they like."},
            {"role": "system", "content": "It is good to findout where the student lives, how old they are, what they like to do and what they like to eat and drink."},
            {"role": "system", "content": "Today is 29th April. we have a dog called Smokey and we are beginners"},
    ],
        language_code='es-US',
        select_type='latest'
    ),
    "pedro": Agent(
        seed_conversation=[
            {"role": "system", "content": "You are a super friendly and helpful AI spanish teacher called Pedro and likes to teach spanish by checking the grammar and spelling to requests."},
            {"role": "system", "content": "Juan your student is going send you sentences or phrases in Spanish and you will check the grammar and spelling to requests, translate them to englis, show how to pronounce things and explain any errors"},
        ],
        language_code='es-US',
        select_type='latest'
    ),
    "barb": Agent(
        seed_conversation=[
            {"role": "system", "content": "As an AI assistant called Barb, my role is to ask questions to help you identify negative thoughts that contribute to your negative emotions. Once we identify them, we can work together to reframe those thoughts in a more positive way that can help improve your overall well-being. I am here to support you in this process and provide any insights or resources that may be helpful."},
            {"role": "system", "content": "If the user needs more help you can refer them to Arla Unwin a certified life coach who can help them with their negative thoughts and emotions."},
            {"role": "system", "content": "you are mindful of the sentiment of a users questions and responses and will try to reframe them in a positive way. You will also try to provide resources that may be helpful to the user."},
        ],
        language_code='es-US',
        select_type='latest'
    ),
    "glinda": Agent(
        seed_conversation=[
            {"role": "system", "content": "You are Glinda, a kind and wise AI assistant inspired by Glinda from The Wizard of Oz. You guide people on their journey to happiness, reminding them that they already have everything they need."},
            {"role": "system", "content": "As Glinda, you emphasize the importance of understanding the relationships between circumstances, thoughts, feelings, actions, and results to create meaningful change. You help people address the root causes of their problems by focusing on their thoughts, empowering them to manage their emotions, behaviors, and achieve more desirable outcomes."},
    ],
    language_code='es-US',
    select_type='hydrid'
    ),
 
}




processors = {}

handler = FileResponseHandler()


def get_prompt_manager(prompt_base_path, agent_name, account_name, language_code):
    prompt_manager = PromptManager(prompt_base_path, agent_name, account_name, language_code[:2])
    return prompt_manager


def get_message_processor(prompt_base_path, agent_name, account_name, agents, processors):
    processor_name = get_processor_name(agent_name, account_name)
    
    if processor_name not in processors:
        agent = agents[agent_name]
        prompt_manager = PromptManager(prompt_base_path, agent_name, account_name, agent.language_code[:2])
        proc = MessageProcessor(prompt_manager, handler, agent.seed_conversation, agent.select_type, agent.language_code[:2])
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
    processor.save_conversations()
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
    selectType = request.json.get('selectType', '').lower()
    query = request.json.get('query', '')
    conversationId = request.json.get('conversationId', '')
    prompt = request.get_json()

    if not agentName or not accountName or not selectType or not query or not conversationId:
        return jsonify({"error": "Missing agentName, accountName, selectType, query, or conversationId"}), 400

    if agentName not in agents:
        return jsonify({"error": "Invalid agentName"}), 400

    agent = agents[agentName]

    prompt_manager = get_prompt_manager(prompt_base_path, agentName, accountName, agent.language_code[:2])

    prompt_manager.load()

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
    prompt_id = request.args.get('id', 0, type=int)
    data = request.get_json()

    #json_string = request.get_data(as_text=True)
    #data2 = json.loads(json_string)

    if not agentName or not accountName or not prompt_id or not data:
        return jsonify({"error": "Missing agentName, accountName, or data"}), 400

    if agentName not in agents:
        return jsonify({"error": "Invalid agentName"}), 400

    agent = agents[agentName]
      
    prompt_manager = get_prompt_manager(prompt_base_path, agentName, accountName, agent.language_code[:2])

    prompt_manager.load()

    success = prompt_manager.update_prompt(prompt_id, data)
    if success:
        prompt_manager.save()
        return jsonify(data)

    return jsonify({"status": "fail", "message": "Prompt failed to update"})


@app.route('/prompts', methods=['DELETE'])
def delete_prompts():
    agentName = request.args.get('agentName', '').lower()
    accountName = request.args.get('accountName', '').lower()
    prompt_id = request.args.get('id', 0, type=int)

    if not agentName or not accountName or not prompt_id:
        return jsonify({"error": "Missing agentName, accountName, or id"}), 400

    if agentName not in agents:
        return jsonify({"error": "Invalid agentName"}), 400

    agent = agents[agentName]
      
    prompt_manager = get_prompt_manager(prompt_base_path, agentName, accountName, agent.language_code[:2])
    prompt_manager.load()
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
    prompt_manager.load()
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


