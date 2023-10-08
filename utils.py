# Description: Utility functions for the app
import openai
import re

#Indicator ID for the end or beginning of a video chain
#Required because of the way Pinecone stores data
NULL_ID = '\0'

def is_null(datum) -> bool:
  return datum == NULL_ID

def get_embedding(text, model="text-embedding-ada-002"):
   text = text.replace("\n", " ")
   return openai.Embedding.create(input = [text], model=model)['data'][0]['embedding']

def extract_video_link_and_start_time(url):
    result = url.split('&t=')
    video_link = result[0]
    start_time = int(result[1]) if len(result) > 1 else 0
    return video_link, start_time

def extract_reference_numbers(text: str) -> list[int]:
    pattern = r"\((\d+(?:,\d+)*)\)"
    matches = re.findall(pattern, text)
    references = [int(ref) for match in matches for ref in match.split(',')]
    return references

def strip_citations(text) -> str:
    pattern = r"\((\d+(?:,\d+)*)\)"
    stripped_text = re.sub(pattern, '', text)
    return stripped_text

