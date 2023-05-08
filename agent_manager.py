import json
from typing import List

#agents = []
#path = './agents.json'

class AgentManager:

    agents = []

    #def __init__(self, path: str = './agents.json'):
    #    self.path = path

    @staticmethod
    def get_agent(name: str) -> dict:
        for agent in AgentManager.agents:
            if agent['name'] == name:
                return agent
            
        return {}

    @staticmethod
    def is_valid(name: str) -> bool:
        
        for agent in AgentManager.agents :
            if agent['name'] == name:
                return True
        return False

    @staticmethod
    def load_agents(agent_path) -> None:
        try:
            with open(agent_path, 'r') as f:
                AgentManager.agents = json.load(f)
        except Exception as e:
            print(e)
            AgentManager.agents = []

    @staticmethod
    def save_agents(agent_path) -> None:
        with open(agent_path, 'w') as f:
            json.dump(AgentManager.agents, f, indent=2)

    @staticmethod
    def get_agent_names() -> List[str]:
        return [agent['name'] for agent in AgentManager.agents]

    @staticmethod
    def get_available_agents() -> List[dict]:
        return AgentManager.agents
