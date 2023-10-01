import chromadb
import openai
import os
import json
import datetime
import csv
from tqdm import tqdm
from dotenv import load_dotenv
from googleapiclient.discovery import build

# Load API keys
load_dotenv()
openai.api_key = os.environ['OPENAI_API_KEY']

def get_search_queries(name):
  queries = [
    f"{name} interview",
    f"{name} remarks", 
    f"{name} townhall",
    f"{name} speech",
    f"{name} press conference",
  ]
  
  return queries

POLITICIANS = [
    "Donald Trump", 
    "Vivek Ramaswamy", 
    "J.D. Vance", 
    "Marjorie Taylor Greene", 
    "Joe Biden", 
    "Barack Obama", 
    "Gretchen Whitmar", 
    "Alexandria Ocasio-Cortez",
    "Ron DeSantis",
    "Bernie Sanders"
]

class YouTubeCrawler:
    def __init__(self, parent):
        self.api_key = None
        self.youtube = None
        self.politician = None
        self.query = None
        self.length = None
        self.num_raw_results = 0
        self.num_results = None
        self.results = None
        self.log = parent.log
        self.crawled_ids = parent.crawled_ids
    
    def set_creds(self):
        self.api_key = os.environ['YOUTUBE_API_KEY']
        self.youtube = build('youtube', 'v3', developerKey=self.api_key)

    def set_politician(self, politician):
        self.politician = politician
    
    def set_query(self, query):
        self.query = query
    
    def set_length(self, length):
        self.length = length
    
    def set_num_results(self, num_results):
        self.num_results = num_results

    def parse_gpt_choice(self, choice: dict) -> dict:
        resp = {}
        text = choice['text']
        #find start of json
        start = text.find("{")
        #find end of json
        end = text.rfind("}")
        #get json
        json_str = text[start:end+1]
        #strip newlines and spaces
        json_str = json_str.replace("\n", "")
        x = json_str.strip()

        #parse json
        try:
            resp = json.loads(x)
        except json.decoder.JSONDecodeError as e:
            print("Error parsing JSON:")
            print(e)
            print("JSON string:")
            print(x)
        return resp

    def apply_content_filter(self, result, k=3) -> bool:
        # setup prompt to only accept content where the politican is speaking and not taken out of context
        politician = self.politician
        #TODO: implement voting system
        content_filter_prompt = f"""
        You are a research analyst, interested in gathering footage of {politician} speaking. You will be given a video to evaluate. Your goal is to determine whether the content is good enough for your research. You only want to see content where the politician is the primary speaker.
        
        % Examples of Permissible Content %
        - Speeches by {politician}
        - Interviews with {politician}
        - Remarks by {politician}
        - Townhalls with {politician}
        - Press conferences with {politician}
        - other Videos of {politician} speaking
        % Examples of Impermissible Content %
        - Hyperpartisan / Hypercritical content
        - Videos of other people talking about {politician}
        - Videos that take {politician}'s words out of context
        - Videos that are not about {politician}
        - Videos where {politician} is not the primary speaker

        First, describe the reasons why the content is permissible or not. Then, answer the following question: Is this video permissible? (y/n). Always return your evaluation as a single JSON object, enclosed in curly brakets. For example:
        
        % Example %
        Title: {politician} speaks at [event]
        Description: {politician} addresses the crowd at [event]
        Channel Title: {politician} News Network
        Published At: 2021-01-01
        {{"reasoning": "This video is a speech by {politician}. It is permissible.", "permissible": "y"}}

        % Your Response %
        Title: {result['title']}
        Description: {result['description']}
        Channel Title: {result['channelTitle']}
        Published At: {result['publishedAt']}
        """

        # create openAI endpoint
        result = openai.Completion.create(
            model="gpt-3.5-turbo-instruct",
            prompt=content_filter_prompt,
            max_tokens=1000,
            n=k
        )

        choices = result['choices']
        json_responses = [ self.parse_gpt_choice(choice) for choice in choices ]

        votes = [ json.get('permissible', None) for json in json_responses ]
        reasons = [ json.get('reasoning', None) for json in json_responses ]

        num_yes = votes.count('y')
        num_no = votes.count('n')
        is_permissible = num_yes > num_no

        if self.log:
            print("Content Filter Call:")
            print("JSON Responses:")
            print(json_responses)
            print("Votes:")
            print(votes)
            print("Reasons:")
            print(reasons)
            print("Is Permissible:")
            print(is_permissible)

        return is_permissible

    def run(self):
        try:
            request = self.youtube.search().list(
                part='snippet',
                q=self.query,
                type='video',
                maxResults=self.num_results,
                order='relevance',
                videoDuration=self.length,
                videoCaption='closedCaption'
            )
            response = request.execute()

        except Exception as e:
            print("Error executing request:")
            print(e)
            print("Query:")
            print(self.query)
            print("Length:")
            print(self.length)
            return

        # # For testing
        # cwrd = os.getcwd()
        # path = os.path.join(cwrd, 'setup/tests/joe-biden-press-conference-50-long/data.json')
        # with open(path, 'r') as f:
        #     response = json.load(f)
        # # End testing

        items = response['items']
        snippets = [ item['snippet'] for item in items ]

        #Check if video is already in database
        videoIds = [ item['id']['videoId'] for item in items ]
        indicator = [ videoId in self.crawled_ids for videoId in videoIds ]

        #Filter out videos that have already been crawled
        items = [ item for item, val in zip(items, indicator) if not val ]
        snippets = [ snippet for snippet, val in zip(snippets, indicator) if not val ]

        #Get raw results
        raw_results = [ {
            'title': snippet['title'],
            'description': snippet['description'],
            'channelTitle': snippet['channelTitle'],
            'publishedAt': snippet['publishedAt'],
            'videoId': item['id']['videoId']
        } for snippet, item in zip(snippets, items) ]

        #Add to number of raw results
        self.num_raw_results += len(raw_results)

        # Filter out bad content
        evals = [ self.apply_content_filter(result) for result in raw_results ]
        results = [ result for result, val in zip(raw_results, evals) if val ]

        self.results = results
    
    def get_results(self):
        return self.results

class Crawler:
    def __init__(self, db, log=False, save=True):
        self.db = db
        self.log = log
        self.crawled_ids = set()
        self.save_crawls = save

        self.crawler = YouTubeCrawler(
            parent=self
        )
        self.crawler.set_creds()

    def run(self, politician, query, k=50, length='medium'):
        if self.log:
            print("Running crawl...")
            print(f"Query: {query}")
            print(f"Video length: {length} ({k} results)")
        
        self.crawler.set_politician(politician)
        self.crawler.set_query(query)
        self.crawler.set_length(length)
        self.crawler.set_num_results(k)
        self.crawler.run()
        results = self.crawler.get_results()

        # Only relevant for similarity filter
        # for result in results:
        #     self.db.add(result)

        #Save crawl
        if self.save_crawls:
            self.save(results)

        if self.log:
            print("Results:")
            print(f"Video length: {length} ({k} results)")
            print(f"Number of raw results: {self.crawler.num_raw_results}")
            print(f"Number of filtered results: {len(results)}")

            #save to log file
            path = os.path.join(os.getcwd(), 'setup/crawl_log.txt')
            with open(path, 'a') as f:
                f.write(f"Query: {query}\n")
                f.write(f"Video length: {length} ({k} results)\n")
                f.write(f"Number of raw results: {self.crawler.num_raw_results}\n")
                f.write(f"Number of filtered results: {len(results)}\n")
                f.write("\n")

    def save(self, results=None):
        if self.log:
            print("Saving crawl...")

        #TODO: this doesn't make sense for saving every time.
        if results is None:
            collection = self.db.store.get(include=['metadatas'])
            metadatas = collection['metadatas']
            ids = collection['ids']

        else:
            if len(results) == 0:
                return
            metadatas = [ result for result in results ]
            ids = [ result['videoId'] for result in results ]

        #Save to csv
        current_date = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        path = os.path.join(os.getcwd(), f'setup/crawls/{current_date}.csv')
        with open(path, 'a+') as f:
            writer = csv.writer(f)
            #Write header
            headers = ['videoId'] + list(metadatas[0].keys())
            writer.writerow(headers)

            #Write each row
            for videoId, metadata in zip(ids, metadatas):
                row = [videoId] + list(metadata.values())
                writer.writerow(row)
                self.crawled_ids.add(videoId)
        
        if self.log:
            print("Done saving crawl.")


class Database:
    def __init__(self):
        self.client = chromadb.Client()
        self.store = self.client.create_collection(
            name='liberate-youtube-crawl',
            metadata={"hnsw:space": "cosine"}
        )

    def __len__(self):
        return len(self.store.get(include=['documents'])['ids'])

    def is_same(self, result1, result2, cosine_similarity, k=3, log=False) -> bool:
        #TODO: this doesn't work at all?
        similarity_filter_prompt = f"""
        You will be given two videos to evaluate. Your goal is to determine whether they cover the same exact event. For instance, both videos could be about the same speech, interview, or press conference.

        <Video 1>
        Title: {result1['title']}
        Description: {result1['description']}
        Channel Title: {result1['channelTitle']}
        Published At: {result1['publishedAt']}
        </Video 1>
        <Video 2>
        Title: {result2['title']}
        Description: {result2['description']}
        Channel Title: {result2['channelTitle']}
        Published At: {result2['publishedAt']}
        </Video 2>
        Cosine Similarity: {cosine_similarity}

        Describe the similarities and differences between the two videos. Then, answer the following question: Do these videos cover the same event? (y/n). Return your answer as a JSON object: {{"description": "The videos cover the same interview", "same": "y"}}
        """

        # create openAI endpoint
        results = openai.Completion.create(
            model="gpt-3.5-turbo-instruct",
            prompt=similarity_filter_prompt,
            max_tokens=500
        )

        response = results['choices'][0]['text']
        print("Similarity Filter Call:")
        print("Response:")
        print(response)
        json_response = self.parse_gpt_choice(results)
        print("JSON Response:")
        print(json_response)

        is_same = json_response['same'] == 'y'
        return is_same


    def get_embedding(self, text, model="text-embedding-ada-002"):
        text = text.replace("\n", " ")
        return openai.Embedding.create(input = [text], model=model)['data'][0]['embedding']

    def add(self, result: dict):

        q = f"""
        title: {result['title']}
        description: {result['description']}
        channelTitle: {result['channelTitle']}
        publishedAt: {result['publishedAt']}
        """
        xq = self.get_embedding(q)

        # #CHECK FOR DUPLICATES
        # if len(self) > 0:
        #     #Check 5 most similar results
        #     k = 5
        #     most_similar_results = self.store.query(
        #         query_embeddings=[xq],
        #         include=['metadatas', 'distances'],
        #         n_results=k
        #     )

        #     #Evaluate similarity
        #     metadatas = most_similar_results['metadatas']
        #     distances = most_similar_results['distances']
        #     print("Most similar results:")
        #     print(metadatas)
        #     print(distances)
        #     for metadata, distance in zip(metadatas, distances):

        #         md = metadata[0]
        #         dist = distance[0]
        #         print(md)
        #         print(dist)

        #         cosine_similarity = 1 - dist

        #         is_same = self.is_same(result, md, cosine_similarity)
        #         if is_same:
        #             #If same, don't add
        #             return

        #TODO: handle HTTPError 403 better
        #Remove videoId
        videoId = result.pop('videoId')
    
        #If not, add it
        self.store.add(
            embeddings=xq,
            metadatas=result,
            ids=videoId
        )

# Path: setup/crawl.py
if __name__ == '__main__':
    db = Database()
    crawl = Crawler(db, save=True)

    # Get all search queries
    query_mat = [
        get_search_queries(politician) for politician in POLITICIANS
    ]
    n_queries_per_politician = len(query_mat[0])

    # Flatten list
    query_iterable = [ item for sublist in query_mat for item in sublist]
    politician_iterable = [ politician for politician in POLITICIANS for i in range(n_queries_per_politician) ]

    iterable = list(zip(politician_iterable, query_iterable))
    
    # Run crawl
    for politician, query in tqdm(iterable):
        crawl.run(
            politician=politician,
            query=query, 
            k=50, 
            length='medium'
        )

    crawl.save()

    # #For testing
    # crawl.run(
    #     politician="Joe Biden",
    #     query="Joe Biden speech", 
    #     k=50, 
    #     length='long'
    # )
    # crawl.run(
    #     politician="Joe Biden",
    #     query="Joe Biden speech", 
    #     k=50, 
    #     length='long'
    # )
    # #End testing

    