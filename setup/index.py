import csv
import os
import sys
import random
import openai
import pinecone
import pickle
from youtube_transcript_api import YouTubeTranscriptApi
from googleapiclient.discovery import build
from dotenv import load_dotenv
from tqdm import tqdm
from node import YTVideo, YTVideoChunk, NULL_ID, is_null, hash_string

def get_embedding(text, model="text-embedding-ada-002"):
   text = text.replace("\n", " ")
   return openai.Embedding.create(input = [text], model=model)['data'][0]['embedding']

if __name__ == '__main__':

    #get delete flag from stdin
    print('Getting delete flag...')
    delete_flag = False
    if len(sys.argv) > 1:
        delete_flag = sys.argv[1] == 'delete'
    print('Delete flag:', delete_flag)

    print('Starting index.py...')

    #load env vars
    print('Loading env vars...')
    load_dotenv()
    YT_api_key = os.getenv('YOUTUBE_API_KEY')
    pinecone_api_key = os.getenv('PINECONE_API_KEY')
    pinecone_env = os.getenv('PINECONE_ENV')
    openai.api_key = os.getenv('OPENAI_API_KEY')
    print('Loaded env vars...')

    #connect to pinecone
    print('Connecting to Pinecone...')
    print('pinecone_api_key:', pinecone_api_key)
    print('pinecone_env:', pinecone_env)
    pinecone.init(api_key=pinecone_api_key, environment=pinecone_env)
    print('Pinecone indexes:', pinecone.list_indexes())
    index_name = 'v1'
    dimensions = 1536

    #delete index if delete flag is set
    if delete_flag and index_name in pinecone.list_indexes():
        pinecone.delete_index(index_name)
        print('Deleted index...')

    if index_name not in pinecone.list_indexes():
        pinecone.create_index(name=index_name, dimension=dimensions, metric='cosine')
        print('Created index...')

    index = pinecone.Index(index_name=index_name)
    print('Connected to Pinecone...')
    
    # #read in csv
    # print('Reading in csv...')
    # cwd = os.getcwd()
    # path = os.path.join(cwd, 'setup/videoids.csv')
    # with open(path) as f:
    #     reader = csv.reader(f)
    #     #skip header
    #     next(reader)
    #     #get video ids and politician names
    #     politician_names, listvideo_ids = zip(*reader)
    #     #make lookup dict
    #     politicians_by_video_id = dict(zip(listvideo_ids, politician_names))
    
    # #Make sure video ids are str
    # listvideo_ids = [ str(video_id) for video_id in listvideo_ids ]
    # # listvideo_ids = listvideo_ids[:10]

    # #get transcript for each video_id
    # print('Getting transcripts...')
    # result = YouTubeTranscriptApi.get_transcripts(
    #     video_ids=listvideo_ids,
    #     languages=['en', 'en-US'],
    #     continue_after_error=True
    # )

    # # extract data from result
    # print('Extracting data...')
    # items = [ (video_id, transcript) for video_id, transcript in result[0].items() ]
    # video_ids, transcripts = zip(*items)

    # politician_names = [ politicians_by_video_id[video_id] for video_id in video_ids ]

    # #get title for each video_id
    # youtube = build('youtube', 'v3', developerKey=YT_api_key)

    # # Get the video details from YouTube Data API
    # print('Getting video details...')
    # video_details = []
    # for i in range(0, len(video_ids), 50):
    #     video_batch = youtube.videos().list(
    #         part='snippet',
    #         id=','.join(video_ids[i:i+50])
    #     ).execute()
    #     video_details.extend(video_batch['items'])
    # print('Extracting video details...')
    # items = [ 
    #     (item['snippet']['title'], item['snippet']['publishedAt']) 
    #     for item in video_details 
    # ]
    # titles, creation_dates = zip(*items)

    # # iterate over data and create YTVideo objects
    # print('Creating YTVideo objects...')
    # ytvids = []
    # iterable = zip(politician_names, video_ids, transcripts, titles, creation_dates)
    # for politician, video_id, transcript, title, creation_date in iterable:
    #     ytvid = YTVideo(
    #         politician,
    #         video_id, 
    #         transcript, 
    #         title, 
    #         creation_date
    #     )
    #     ytvids.append(ytvid)

    # #store YTVideo objects as pickle
    # print('Storing YTVideo objects...')
    # path = os.path.join(cwd, 'setup/embeds.pkl')
    # with open(path, 'wb') as f:
    #     pickle.dump(ytvids, f)
    
    # OPTIONAL LINE: read in YTVideo objects from pickle
    print('Reading in YTVideo objects...')
    cwd = os.getcwd()
    path = os.path.join(cwd, 'setup/embeds.pkl')
    with open(path, 'rb') as f:
        ytvids = pickle.load(f)

    #upsert data for each video
    print('Upserting data...')
    for vid in tqdm(ytvids):
        texts = vid.get_chunk_transcripts()
        metadatas = vid.get_chunk_metadatas()
        ids = vid.get_chunk_ids()

        politician = vid.politican
        title = vid.title
        created = vid.created

        embedding_texts = [ 
        f"""This is a transcript of a video of {politician} speaking.
        The video was created on {created}.
        The title of the video is {title}.
        The transcript is as follows:
        "{text}"
        """
        for text in texts
        ]

        embeds = [ get_embedding(text) for text in embedding_texts ]

        for i, md in enumerate(metadatas):
            md['transcript'] = texts[i]

        to_upsert = zip(ids, embeds, metadatas)

        upsert_response = index.upsert(
            vectors=to_upsert
        )
