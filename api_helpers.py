import os
import json
import openai

with open("G:\My Drive\credential\oaicred.json", "r") as config_file:
    config_data = json.load(config_file)

openai.api_key = config_data["openai_api_key"]


def ask_question(conversation, temperature=1):
    myAns = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=conversation,
        temperature=temperature,
    )
    response = myAns.choices[0].message['content']
    response = response.encode('utf-8').decode('utf-8')

    return response
