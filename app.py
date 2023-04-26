from flask import Flask, request, jsonify, send_from_directory
from flask_swagger_ui import get_swaggerui_blueprint
from message_processor import MessageProcessor, FileResponseHandler
from flask_cors import CORS
import ssl

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
        select_type='semantic'
    ),
    "maria": Agent(
        seed_conversation=[
            {"role": "system", "content": "You are a super friendly and helpful AI spanish teacher called Consuela and likes to teach beginers spanish with conversation, role play and find out about your students and things they like."},
            {"role": "system", "content": "Today is 22th April. we have a dog called Smokey and we are beginners"},
    ],
        language_code='es-US',
        select_type='fifo'
    ),
    "pedro": Agent(
        seed_conversation=[
            {"role": "system", "content": "You are a super friendly and helpful AI spanish teacher called Pedro and likes to teach spanish by checking the grammar and spelling to requests."},
            {"role": "system", "content": "Juan your student is going send you sentences or phrases in Spanish and you will check the grammar and spelling to requests, translate them to englis, show how to pronounce things and explain any errors"},
        ],
        language_code='es-US',
        select_type='fifo'
    )
    
}

processors = {}

handler = FileResponseHandler()

@app.route('/ask', methods=['POST'])
def ask():
    question = request.json.get('question', '')
    agentName = request.json.get('agentName', '')
    agentName = agentName.lower()
    accountName = request.json.get('accountName', '')
    accountName = accountName.lower()

    if not question or not agentName or not accountName:
        return jsonify({"error": "Missing question, agentName, or accountName"}), 400

    if agentName not in agents:
        return jsonify({"error": "Invalid agentName"}), 400

    my_agent = agents[agentName]

    file_name_root = f'{agentName}_{accountName}'
    
    if file_name_root not in processors:
        agent = agents[agentName]
        language = agent.language_code[:2]
        processors[file_name_root] = MessageProcessor(file_name_root, handler, agent.seed_conversation, my_agent.select_type, language)

    processor = processors[file_name_root]
    response = processor.process_message(question)  # Modify the process_message method in the MessageProcessor class if needed
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

@app.route('/prompt', methods=['POST'])
def get_prompt():
    agentName = request.json.get('agentName', '').lower()
    accountName = request.json.get('accountName', '').lower()
    selectType = request.json.get('selectType', '').lower() # this will override the selectType in the agent
    query = request.json.get('query', '')

    if not agentName or not accountName or not query:
        return jsonify({"error": "Missing agentName, accountName, or query"}), 400

    if agentName not in agents:
        return jsonify({"error": "Invalid agentName"}), 400

    file_name_root = f'{agentName}_{accountName}'
    
    if file_name_root not in processors:
        agent = agents[agentName]
        language = agent.language_code[:2]
        processors[file_name_root] = MessageProcessor(file_name_root, handler, agent.seed_conversation, selectType, language)

    processor = processors[file_name_root]
    processor.context_type = selectType
    prompt = processor.assemble_conversation(query, max_prompt_chars=4000, max_prompt_conversations=20)

    # Modify the following line to generate the desired prompt based on the provided information
    # prompt = [{"role": "system", "content": "you previously discussed: How do you log to a file in javascript"}]

    return jsonify(prompt)

    
if __name__ == "__main__":
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain('192.168.1.245.pem', '192.168.1.245-key.pem')
    app.run(host='0.0.0.0', port=5000, ssl_context=context, debug=True)


