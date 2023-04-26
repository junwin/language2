import json
from typing import List, Dict
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


nltk.download('wordnet')
nltk.download('punkt')


class ConversationManager:
    def __init__(self, language_code = "en"):
        self.prompts = {"prompts": []}
        self.language_code = language_code
        if language_code == "es":
            self.nlp = spacy.load("es_core_news_sm")
        else:
            self.nlp = spacy.load("en_core_web_sm")
        try:
            nltk.data.find("tokenizers/punkt")
        except LookupError:
            nltk.download("punkt")


    def store_conversation(self, conversations: List[Dict[str, str]], conversationId) -> None:
        conversation_id = time.time_ns()
        utc_timestamp = datetime.utcnow().isoformat() + 'Z'  # ISO 8601 format
        total_chars = sum(len(conv["content"]) for conv in conversations)
        keywords = set()

        for conv in conversations:
            content = conv["content"]
            keywords |= set(self.extract_keywords(content))

        conversation = {
            "id": conversation_id,
            "utc_timestamp": utc_timestamp,  # UTC timestamp as  ISO 8601 - 2019-11-14T00:55:31.820Z
            "total_chars": total_chars,
            "conversation": conversations,
            "keywords": list(keywords),
            "conversationId": conversationId
        }
        self.prompts["prompts"].append(conversation)




    def extract_keywords(self, content: str, top_n: int = 5) -> List[str]:
        # Process the content using SpaCy
        doc = self.nlp(content.lower())

        # Filter out punctuation, stopwords, and only keep PROPN and NOUN
        filtered_tokens = [token for token in doc if not token.is_punct and not token.is_stop and token.pos_ in ["PROPN", "NOUN"]]

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


    def find_closest_conversation(self, input_text: str, number_to_return=2, min_similarity_threshold=0) -> List[Dict]:
        tokenized_text = self.tokenize(input_text)
        conversations = self.prompts

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






    def concatenate_content(self, conversation_data):
        conversation = conversation_data["conversation"]
        concatenated_content = ""
        for message in conversation:
            concatenated_content += message["content"] + " "
        return concatenated_content.strip()



    def find_latest_conversation(self, number_to_return: int) -> List[Dict]:
        if len(self.prompts["prompts"]) > 0:
            sliced_list = self.prompts["prompts"][-number_to_return:]
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

        for conv in self.prompts["prompts"]:
            if match_all:
                if all(keyword in conv["keywords"] for keyword in keywords):
                    matched_prompt_ids.add(conv["id"])
            else:
                if any(keyword in conv["keywords"] for keyword in keywords):
                    matched_prompt_ids.add(conv["id"])

        matched_conversations = [
            (prompt["id"], item) for prompt in self.prompts["prompts"] if prompt["id"] in matched_prompt_ids for item in prompt["conversation"]]

        result = []
        for conv_id, conv_item in matched_conversations:
            parent_prompt = [prompt for prompt in self.prompts["prompts"] if prompt["id"] == conv_id][0]
            conv_item["utc_timestamp"] = parent_prompt["utc_timestamp"]
            result.append(conv_item)

        return result


    def save(self, path: str) -> None:
        with open(path, 'w') as f:
            json.dump(self.prompts, f)


    def load(self, path: str) -> None:
        with open(path, 'r') as f:
            self.prompts = json.load(f)