import json
from typing import List, Dict, Set
import time
import string
from collections import Counter
from nltk.stem import SnowballStemmer
from nltk.tokenize import word_tokenize
import nltk

import spacy
from nltk.corpus import wordnet as wn
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
from datetime import datetime
from spacy.lang.en import STOP_WORDS


nltk.download('wordnet')
nltk.download('punkt')


class PromptManager:
    def __init__(self, base_path, agent_name, account_name, language_code = "en"):
        self.prompts_data = {"prompts": []}
        self.language_code = language_code
        if language_code == "es":
            self.nlp = spacy.load("es_core_news_sm")
        else:
            self.nlp = spacy.load("en_core_web_sm")
        try:
            nltk.data.find("tokenizers/punkt")
        except LookupError:
            nltk.download("punkt")
        self.agent_name = agent_name
        self.account_name = account_name
        self.base_path = base_path

    def get_id(self) -> str:
        return str(time.time_ns()) 

    def store_prompt_conversations(self, conversations: List[Dict[str, str]], conversationId) -> None:
        id = self.get_id()
        utc_timestamp = datetime.utcnow().isoformat() + 'Z'  # ISO 8601 format
        total_chars = sum(len(conv["content"]) for conv in conversations)
        keywords = set()

        for conv in conversations:
            content = conv["content"]
            keywords |= set(self.extract_keywords(content))

        conversation = {
            "id": id,
            "utc_timestamp": utc_timestamp,  # UTC timestamp as  ISO 8601 - 2019-11-14T00:55:31.820Z
            "total_chars": total_chars,
            "conversation": conversations,
            "keywords": list(keywords),
            "conversationId": conversationId
        }
        self.prompts_data["prompts"].append(conversation)


    def store_prompt(self, prompt: Dict) -> bool:
        prompt['id'] = self.get_id()
        prompt['utc_timestamp'] = datetime.utcnow().isoformat() + 'Z'
        prompt['keywords'] = list(self.get_conversation_keywords(prompt['conversation']))
        prompt['total_chars'] = sum(len(conv['content']) for conv in prompt['conversation'])

        self.prompts_data['prompts'].append(prompt)
        return True



    def get_conversation_keywords(self, conversations: List[dict]) -> Set[str]:
        keywords = set()

        for conv in conversations:
            content = conv["content"]
            extracted_keywords = set(self.extract_keywords(content))
            keywords.update(extracted_keywords)

        return keywords


    def update_prompt(self, prompt_id: string, updated_prompt: Dict) -> bool:
        for prompt in self.prompts_data["prompts"]:
            if prompt["id"] == prompt_id:
                prompt.update(updated_prompt)
                return True
        return False


    def delete_prompt(self, prompt_id: string) -> bool:
        for index, prompt in enumerate(self.prompts_data["prompts"]):
            if prompt["id"] == prompt_id:
                del self.prompts_data["prompts"][index]
                return True
        return False

    def extract_keywords(self, content: str, top_n: int = 10) -> List[str]:
        # Process the content using SpaCy
        doc = self.nlp(content.lower())

        # Filter out punctuation, stopwords, and only keep PROPN and NOUN
        # Remove punctuation
        no_punct_tokens = [token for token in doc if not token.is_punct]

        # Remove stopwords
        no_stop_tokens = [token for token in no_punct_tokens if token.text not in STOP_WORDS]

        # Keep only PROPN and NOUN
        filtered_tokens = [token for token in no_stop_tokens if token.pos_ in ["PROPN", "NOUN", "VERB"]]
    
        # Perform lemmatization
        lemmatized_words = [token.lemma_ for token in filtered_tokens]
        
        # Count word frequency
        word_frequency = Counter(lemmatized_words)
        
        # Choose top N words as keywords
        keywords = [word for word, freq in word_frequency.most_common(top_n)]

        return keywords



    def concatenate_keywords(self, conversation_data):
        keywords = conversation_data["keywords"]
        concatenated_keywords = " ".join(keywords)
        return concatenated_keywords

    def tokenize(self, text):
        return nltk.word_tokenize(text)

    def semantic_similarity(self, set1, set2):
        vectorizer = TfidfVectorizer()
        tfidf_matrix = vectorizer.fit_transform([" ".join(set1), " ".join(set2)])
        return cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])


    def find_closest_promptIds(self, input_text: str, number_to_return=2, min_similarity_threshold=0) -> List[str]:
        my_keywords = self.extract_keywords(input_text)
        tokenized_text = self.tokenize(input_text)
        tokenized_text = my_keywords
        prompts = self.prompts_data["prompts"]

        prompt_similarities = []

        for prompt in prompts:
            concat_text = self.concatenate_content(prompt)
            concatenate_keywords = self.concatenate_keywords(prompt)
            similarity = self.semantic_similarity(tokenized_text, self.tokenize(concatenate_keywords))

            if similarity > min_similarity_threshold:
                prompt_similarities.append((prompt["id"], similarity))

        # Sort the prompt IDs by similarity
        sorted_prompt_ids = sorted(prompt_similarities, key=lambda x: x[1], reverse=True)

        # Select and return the N prompt IDs with the highest similarities
        return [prompt_id[0] for prompt_id in sorted_prompt_ids[:number_to_return]]


    def find_latest_promptIds(self, number_to_return: int) -> List[str]:
        prompts = self.prompts_data["prompts"]

        if len(prompts) > 0:
            sliced_list = prompts[-number_to_return:]
            result = [prompt["id"] for prompt in sliced_list]
            return result

        return []



    def find_closest_conversation(self, input_text: str, number_to_return=2, min_similarity_threshold=0) -> List[Dict]:
        tokenized_text = self.tokenize(input_text)
        conversations = self.prompts_data

        collected_conversations = []

        for prompt in conversations["prompts"]:
            concat_text = self.concatenate_content(prompt)
            concatenate_keywords = self.concatenate_keywords(prompt)
            # similarity = self.semantic_similarity(tokenized_text, prompt["keywords"])
            # similarity = self.semantic_similarity(tokenized_text, self.tokenize(concat_text))
            similarity = self.semantic_similarity(tokenized_text, self.tokenize(concatenate_keywords))
            # print (similarity)
            # print (concat_text)
            if similarity > min_similarity_threshold:
                # Copy the conversation and add the similarity and utc_timestamp
                conversation = [conv.copy() for conv in prompt["conversation"]]
                for conv in conversation:
                    conv["utc_timestamp"] = prompt["utc_timestamp"]
                    conv["similarity"] = similarity

                collected_conversations.append(conversation)

        # Flatten the list of conversations and sort by similarity
        flat_conversations = [conv for sublist in collected_conversations for conv in sublist]
        sorted_conversations = sorted(flat_conversations, key=lambda x: x["similarity"], reverse=True)

        # Select and return the N conversations with the highest similarities
        return sorted_conversations[:number_to_return]






    def concatenate_content(self, prompt):
        conversation = prompt["conversation"]
        concatenated_content = ""
        for message in conversation:
            concatenated_content += message["content"] + " "
        return concatenated_content.strip()

    def find_keyword_promptIds(self, content_text: str, match_all=False, number_to_return=None) -> List[str]:
        keywords = self.extract_keywords(content_text, 10)
        matched_prompt_ids = set()

        for conv in self.prompts_data["prompts"]:
            if match_all:
                if all(keyword in conv["keywords"] for keyword in keywords):
                    matched_prompt_ids.add(conv["id"])
            else:
                if any(keyword in conv["keywords"] for keyword in keywords):
                    matched_prompt_ids.add(conv["id"])

        # Convert the set of matched prompt IDs to a list
        matched_prompt_ids_list = list(matched_prompt_ids)

        # Return the specified number of prompt IDs, if provided
        if number_to_return is not None:
            return matched_prompt_ids_list[:number_to_return]

        return matched_prompt_ids_list

    def find_latest_conversation(self, number_to_return: int) -> List[Dict]:
        if len(self.prompts_data["prompts"]) > 0:
            sliced_list = self.prompts_data["prompts"][-number_to_return:]
            result = []
            for prompt in sliced_list:
                conversation = prompt["conversation"]
                for conv in conversation:
                    conv["utc_timestamp"] = prompt["utc_timestamp"]
                result.extend(conversation)
            return result
        return []


    def get_conversations(self, content_text: str, match_all=False) -> List[Dict]:
        keywords = self.extract_keywords(content_text, 10)
        matched_prompt_ids = set()

        for conv in self.prompts_data["prompts"]:
            if match_all:
                if all(keyword in conv["keywords"] for keyword in keywords):
                    matched_prompt_ids.add(conv["id"])
            else:
                if any(keyword in conv["keywords"] for keyword in keywords):
                    matched_prompt_ids.add(conv["id"])

        matched_conversations = [
            (prompt["id"], item) for prompt in self.prompts_data["prompts"] if prompt["id"] in matched_prompt_ids for item in prompt["conversation"]]

        result = []
        for conv_id, conv_item in matched_conversations:
            parent_prompt = [prompt for prompt in self.prompts_data["prompts"] if prompt["id"] == conv_id][0]
            conv_item["utc_timestamp"] = parent_prompt["utc_timestamp"]
            result.append(conv_item)

        return result


    def get_conversations_ids(self, ids: List[str]) -> List[Dict]:
        matching_conversations = []

        for prompt in self.prompts_data["prompts"]:
            if prompt["id"] in ids:
                conversation = prompt["conversation"]
                matching_conversations.extend(conversation)

        return matching_conversations

    def get_conversations(self, conversation_id: str) -> List[Dict]:
        matching_conversations = []

        for prompt in self.prompts_data["prompts"]:
            if prompt["conversationId"] == conversation_id:
                conversation = prompt["conversation"]
                for conv in conversation:
                    conv["utc_timestamp"] = prompt["utc_timestamp"]
                matching_conversations.extend(conversation)

        return matching_conversations

    def get_prompts(self, conversation_id: str) -> List[Dict]:
        matching_prompts = []

        for prompt in self.prompts_data["prompts"]:
            if prompt["conversationId"] == conversation_id:
                matching_prompts.append(prompt)

        return matching_prompts

    def get_prompt(self, id: string) -> List[Dict]:
        for prompt in self.prompts_data["prompts"]:
            if prompt["id"] == id:
                return prompt
        return []

    def get_conversation_text(self, prompt, separator="--") -> Dict[str, str]:
        conversation_text = {}

        for conversation in prompt["conversation"]:
            role = conversation["role"]
            content = conversation["content"]

            if role not in conversation_text:
                conversation_text[role] = content
            else:
                conversation_text[role] += f"{separator} {content}"

        return conversation_text
    
    def get_formatted_text(self, source_text: Dict[str, str]) -> str:
        formatted_text = ""
        for key, value in source_text.items():
            formatted_text += f"{key}: {value}\n"
        return formatted_text.strip()

    def get_conversation_text_by_id(self, conversation_id: str, separator="--") -> str:
        response_text = ""
        prompts = self.get_prompts(conversation_id)
        for prompt in prompts:
            myText = self.get_formatted_text(self.get_conversation_text(prompt))
            response_text += f"{myText}\n"
            
        return response_text
        

    def get_complete_path(self, base_path, agent_name, account_name):
        full_path = base_path + '/' + agent_name + '_' + account_name + '_conv.json'
        return full_path

    def save(self) -> None:
        path = self.get_complete_path(self.base_path, self.agent_name, self.account_name)
        with open(path, 'w') as f:
            json.dump(self.prompts_data, f)


    def load(self) -> None:
        path = self.get_complete_path(self.base_path, self.agent_name, self.account_name)
        try:
            with open(path, 'r') as f:
                self.prompts_data = json.load(f)
        except FileNotFoundError:
            # If the file is not found, set prompts_data to an empty list or default value
            self.prompts_data = {'prompts': []}


    def get_distinct_conversation_ids(self) -> List[str]:
        conversation_ids = set()
        for prompt in self.prompts_data['prompts']:
            conversation_ids.add(prompt['conversationId'])
        return list(conversation_ids)

    def change_conversation_id(self, old_id: str, new_id: str) -> None:
        for prompt in self.prompts_data['prompts']:
            if prompt['conversationId'] == old_id:
                prompt['conversationId'] = new_id