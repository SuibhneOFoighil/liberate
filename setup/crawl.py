import chromadb
import openai
import os
import json
import datetime
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
    f"{name} lecture"
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
    def __init__(self):
        self.api_key = None
        self.youtube = None
        self.politician = None
        self.query = None
        self.length = None
        self.num_raw_results = 0
        self.num_results = None
        self.results = None
    
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

    def apply_content_filter(self, result, k=3) -> bool:
        # setup prompt to only accept content where the politican is speaking and not taken out of context
        politician = self.politician
        content_filter_prompt = f"""
        You are a political analyst, interested in understanding the views of the politician, {politician}. You will be given a video to evaluate. Your goal is to determine whether the content is valuable or not. You only want to see content where the politician is speaking and not taken out of context. The following content is permissible:
        - Speeches by {politician}
        - Interviews with {politician}
        - Remarks by {politician}
        - Townhalls with {politician}
        - Press conferences with {politician}
        - other Videos of {politician} expressing their views
        The following content is not permissible:
        - Hyperpartisan content
        - Videos that take {politician}'s words out of context
        - Videos that are not about {politician}
        - Clickbait videos

        Data will be presented in the following format:
        <Video Title>
        <Video Description>
        <Video Channel Title>
        <Video Published At>

        % Data %
        <Video Title> {result['title']} </Video Title>
        <Video Description> {result['description']} </Video Description>
        <Video Channel Title> {result['channelTitle']} </Video Channel Title>
        <Video Published At> {result['publishedAt']} </Video Published At>
        % End Data %

        Please describe the content of the video. Then, answer the following question: Is this video permissible? (y/n). Return your answer as a JSON object: {{"description": "The video is a speech by {politician} about the economy", "permissible": "y"}}
        """

        # # create openAI endpoint
        results = openai.Completion.create(
            model="gpt-3.5-turbo-instruct",
            prompt=content_filter_prompt,
            n=3,
        )
        choices = results['choices']
        responses = [ choice['text'] for choice in choices ]

        # get majority vote
        yes = responses.count('y')
        no = responses.count('n')
        return yes > no

    def run(self):
        # request = self.youtube.search().list(
        #     part='snippet',
        #     q=self.query,
        #     type='video',
        #     maxResults=self.num_results,
        #     order='relevance',
        #     videoDuration=self.length
        # )
        # response = request.execute()

        # For testing
        cwrd = os.getcwd()
        path = os.path.join(cwrd, 'setup/ex.json')
        with open(path, 'r') as f:
            response = json.load(f)
        # End testing

        items = response['items']
        snippets = [ item['snippet'] for item in items ]
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
        results = [ result for result, val in zip(raw_results, evals) if not val ]

        self.results = results
    
    def get_results(self):
        return self.results

class Crawler:
    def __init__(self, db):
        self.db = db
        self.crawler = YouTubeCrawler()
        self.crawler.set_creds()

    def run(self, politician, query, k=50, length='medium', log=False):
        
        if log:
            print(f"Running query: {query}")
            initial_len = len(self.db)

        self.crawler.set_politician(politician)
        self.crawler.set_query(query)
        self.crawler.set_length(length)
        self.crawler.set_num_results(k)
        self.crawler.run()
        results = self.crawler.get_results()
        for result in results:
            self.db.add(result)

        if log:
            print("Results:")
            print(f"Video length: {length} ({k} results)")
            print(f"Number of raw results: {self.crawler.num_raw_results}")
            print(f"Number of results: {len(results)}")
            print(f"Number of new results: {len(self.db) - initial_len}")

            #save to log file
            with open('crawl_log.txt', 'a') as f:
                f.write(f"Query: {query}\n")
                f.write(f"Video length: {length} ({k} results)\n")
                f.write(f"Number of raw results: {self.crawler.num_raw_results}\n")
                f.write(f"Number of results: {len(results)}\n")
                f.write(f"Number of new results: {len(self.db) - initial_len}\n")
                f.write("\n")

    def save(self, log=False):
        if log:
            print("Saving crawl...")

        #Get collection
        collection = self.db.store.get(include=['documents'])

        #Save as csv
        current_date = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        path = os.path.join(os.getcwd(), f'crawls/{current_date}.csv')
        with open('crawl.csv', 'w') as f:
            f.write("title,description,channelTitle,publishedAt,videoId\n")
            for document in collection['documents']:
                f.write(f"{document['title']},{document['description']},{document['channelTitle']},{document['publishedAt']},{document['videoId']}\n")
        
        if log:
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
        You will be given two videos to evaluate. Your goal is to determine whether they are about the same event or not. Please describe the similarities and differences between the two videos. Then, answer the following question: Are these videos about the same event? (y/n)

        Data will be presented in the following format:
        <Video 1 Title> | <Video 2 Title>
        <Video 1 Description> | <Video 2 Description>
        <Video 1 Channel Title> | <Video 2 Channel Title>
        <Video 1 Published At> | <Video 2 Published At>
        <Cosine Similarity>

        % Data %
        Video 1 Title: {result1['title']} | Video 2 Title: {result2['title']}
        Video 1 Description: {result1['description']} | Video 2 Description: {result2['description']}
        Video 1 Channel Title: {result1['channelTitle']} | Video 2 Channel Title: {result2['channelTitle']}
        Video 1 Published At: {result1['publishedAt']} | Video 2 Published At: {result2['publishedAt']}
        Cosine Similarity: {cosine_similarity}
        % End Data %

        Describe the similarities and differences between the two videos. Then, answer the following question: Are these videos about the same event? (y/n). Return your answer as a JSON object: {{"description": "The titles are roughly the same in both videos and both were published on December 1st by different media outlets", "same": "y"}}
        """

        # create openAI endpoint
        results = openai.Completion.create(
            model="gpt-3.5-turbo-instruct",
            prompt=similarity_filter_prompt,
            n=k,
        )

        responses = [ result['text'] for result in results['choices'] ]
        print("Responses:")
        print(responses)
        print(type(responses))
        
        descriptions = [ response['description'] for response in responses ]
        votes = [ response['same'] for response in responses ]

        if log:
            print("Responses:")
            for response in responses:
                print(response)
            print("Votes:")
            print(votes)

        # get majority vote
        yes = votes.count('y')
        no = votes.count('n')
        return yes > no

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

        if len(self) > 0:
            #Check 5 most similar results
            k = 5
            most_similar_results = self.store.query(
                query_embeddings=[xq],
                include=['metadatas', 'distances'],
                n_results=k
            )

            #Evaluate similarity
            metadatas = most_similar_results['metadatas']
            distances = most_similar_results['distances']
            print("Most similar results:")
            print(metadatas)
            print(distances)
            for metadata, distance in zip(metadatas, distances):

                md = metadata[0]
                dist = distance[0]
                print(md)
                print(dist)

                cosine_similarity = 1 - dist

                is_same = self.is_same(result, md, cosine_similarity)
                if is_same:
                    #If same, don't add
                    return

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
    crawl = Crawler(db)
    # for politician in POLITICIANS:
    #     queries = get_search_queries(politician)
    #     for query in queries:
    #         for length in ['medium', 'long']:
    #             crawl.run(
    #                 politician=politician,
    #                 query=query, 
    #                 k=50, 
    #                 length=length, 
    #                 log=True
    #             )

    #For testing
    crawl.run(
        politician="Donald Trump",
        query="Donald Trump interview", 
        k=50, 
        length='medium', 
        log=True
    )
    #End testing

    crawl.save(log=True)