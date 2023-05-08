import os
import json
import openai

with open("G:\My Drive\credential\oaicred.json", "r") as config_file:
    config_data = json.load(config_file)

openai.api_key = config_data["openai_api_key"]


def ask_question(conversation, model="gpt-3.5-turbo", temperature=0):
    myAns = openai.ChatCompletion.create(
        model=model,
        messages=conversation,
        temperature=temperature,
    )
    response = myAns.choices[0].message['content']
    response = response.encode('utf-8').decode('utf-8')

    return response

def get_completion(prompt, temperature=0, model="gpt-3.5-turbo"):
    messages = [{"role": "user", "content": prompt}]
    response = openai.ChatCompletion.create(
        model=model,
        messages=messages,
        temperature=temperature, # this is the degree of randomness of the model's output
    )
    return response.choices[0].message["content"]

def get_completion_from_messages(messages, model="gpt-3.5-turbo", temperature=0):
    response = openai.ChatCompletion.create(
        model=model,
        messages=messages,
        temperature=temperature, # this is the degree of randomness of the model's output
    )

    return response.choices[0].message["content"]
