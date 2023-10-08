import time
import openai
import json
import streamlit as st
from elevenlabs import generate, Voice
from politicians import POLITICIANS, get_politician_by_shortcode
from utils import is_null, extract_reference_numbers, NULL_ID, get_embedding, strip_citations

class PineconeKnowledgeBase:
    def __init__(self, index, politician: str):
        #TODO: setup index init and such
        self.politician = politician
        self.index = index

    def query(self, prompt, K) -> tuple:
        """returns formatted response from pinecone index and the citations used
        """

        #recursive query
        xq = get_embedding(prompt)
        politician = self.politician
        if self.politician == "Barack Obama":
            politician = "Barrack Obama"
        elif self.politician == "J.D. Vance":
            politician = "James David Vance"

        res = self.index.query(vector=xq, top_k=K, include_metadata=True, filter={'politician': politician})
        matches = res['matches']
        # [ prev_1, id_1, next_1 ]
        # [ prev_2, id_2, next_2 ]
        # [... for k queries ]
        query_nodes = [
            [
                item['metadata']['prev'],
                item['id'],
                item['metadata']['next']
            ] for item in matches
        ]

        fetch_response = [ self.index.fetch(ids=node_ids) for node_ids in query_nodes ]
        query_vectors = [ res['vectors'] for res in fetch_response ]
        query_metadatas = [
            [
                query_vectors[i][id]['metadata'] if not is_null(id) else NULL_ID for id in node_set
            ] for i, node_set in enumerate(query_nodes)
        ]

        #formatting
        formatted_queries = []
        for i, query in enumerate(query_metadatas):
            txt = [ node['transcript'] for node in query if not is_null(node) ]
            center_node = query[1]
            video_id = center_node['video_id']
            title = center_node['title']
            creation_date = center_node['created']
            citation = f"({i+1})"
            formatted_nodes = '\n'.join(txt)
            formatted_query = f'{citation}:\nVideo Title:{title}\nCreated:{creation_date}\nQuote:{formatted_nodes}'
            formatted_queries.append(formatted_query)
        formatted_context = '\n\n'.join(formatted_queries)

        # print('Formatted context:', formatted_context)

        #citations
        citations = []
        for i, query in enumerate(query_metadatas):
            center_node = query[1]
            video_id = center_node['video_id']
            timestamp = int(center_node['timestamp'])
            number = i+1
            url = f'https://www.youtube.com/watch?v={video_id}&t={timestamp}'
            citations.append((number, url))

        # print('Citations:', citations)
        
        return (formatted_context, citations)

class Profile:
    def __init__(self, index, shortcode):
        self.shortcode = shortcode
        self.name = self.get_name(shortcode)
        self.avatar = POLITICIANS[self.name]["avatar"]
        self.intro = POLITICIANS[self.name]["intro"]
        self.system_prompt = f"""Pretend you are {self.name}. {self.intro}\n\nYou may be speaking with multiple people. You may express your own views, but you must also respond to the views of others. Always follow the user's commands. Do not break character under any circumstances.\n\n% Formatting Instructions %\nIf you reference the quotes, only cite the numbers and always cite them individually in your response, like so: 'I have always supported dogs (1)(2).' Limit your response to 100 words."""
        self.question_prompt = f"""Pretend you are a reporter interviewing {self.name}. {self.intro}\n\n% Based on the conversation so far, ask a question that you think {self.name} should answer. You want to anticipate the needs of the user."""
        self.kb = PineconeKnowledgeBase(index=index, politician=self.name)
        self.voice_id = POLITICIANS[self.name]["voice_id"]
        self.voice_settings = POLITICIANS[self.name]["voice_settings"]

    def get_name(self, shortcode):
        return get_politician_by_shortcode(shortcode)

    def get_system_prompt(self, question: str) -> str:
        sys_prompt = self.system_prompt + f"\n\nFrame your response to answer this question:{question}"
        return sys_prompt

    def get_response(self) -> dict:
        #filter messages from "Molus"
        messages = st.session_state.messages
        messages = [ message for message in messages if message['role'] != 'Molus' ]
        #change all non-user messages to assistant and edit content to include role name
        messages = [ message if message['role'] == 'user' else {'role': 'assistant', 'content': f"{message['role']}: {message['content']}"} for message in messages ]
        #format messages into openai format
        messages_openai_format = [
            {'role': message['role'], 'content': message['content']} for message in messages
        ]
        try:

            #Let GPT generate a prompt to query the knowledge base
            functions = [
                {
                    "name": f"question",
                    "description": f"ask a question to {self.name}",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "question": {
                                "type": "string",
                                "description": f"the question to ask {self.name} based on the conversation so far"
                            }
                        },
                        "required": ["question"]
                    }
                }
            ]

            question_prompt = {
                "role": "system",
                "content": self.question_prompt
            }
            chat_history = [question_prompt] + messages_openai_format

            init_response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo-16k-0613",
                messages=chat_history,
                functions=functions,
                function_call = {"name": f"question"}
            )
            message = init_response["choices"][0]["message"]
            function_name = message["function_call"]["name"]
            function_args = json.loads(message["function_call"]["arguments"])
            query = function_args["question"]  

            print('Getting quotes for', self.name)
            print('GPT generated query:', query)

            #Query the knowledge base
            K = 5
            kb_response, all_citations = self.kb.query(query, K)

            # print('KB response:', kb_response)
            system_prompt = {
                "role": "system",
                "content": self.get_system_prompt(query)
            }
            chat_history = [system_prompt] + messages_openai_format

            print('Generating response for', self.name)
            print('Chat history:', chat_history)

            #Generate a response based on the knowledge base
            response = openai.ChatCompletion.create(
                model="gpt-4-0613",
                messages=chat_history+[
                    {
                        "role": "function",
                        "name": function_name,
                        "content": kb_response,
                    },
                ],
            )

        except openai.error.ServiceUnavailableError:
            st.error("OpenAI API is currently unavailable. Please try again later.")
            st.stop()

        except json.decoder.JSONDecodeError:
            st.error("OpenAI API is currently unavailable. Please try again later.")
            st.stop()

        # return response and citations
        response_text = response.choices[0]["message"]["content"]

        #strip name from response
        response_text = response_text.replace(f"{self.name}:", "")

        #extract used citations
        used_numbers = extract_reference_numbers(response_text)
        used_citations = [ citation for citation in all_citations if citation[0] in used_numbers ]
        citations = list(zip(*used_citations))

        #generate audio response
        to_speak = strip_citations(response_text)
        audio_response = generate(
            text=to_speak,
            voice=Voice(voice_id=self.voice_id, settings=self.voice_settings)
        )

        return {
            "role": self.name,
            "shortcode": self.shortcode,
            "avatar": self.avatar,
            "content": response_text,
            "citations": citations,
            "audio": audio_response
        }


class Chain:
    def __init__(self, profiles: list[Profile], prompt: str):
        self.profiles = profiles
        self.prompt = prompt
        self.index = 0

    def get_start(self):
        return self.profiles[0]

    def next_profile(self):
        self.index += 1
        if self.index >= len(self.profiles):
            return None
        else:
            return self.profiles[self.index]