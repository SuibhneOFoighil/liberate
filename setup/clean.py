#Purpose: take crawl list and further refine with more details about videos
import openai
import json
import pandas as pd
from googleapiclient.discovery import build
from dotenv import load_dotenv
from tqdm import tqdm
import os

load_dotenv()
YOUTUBE = build('youtube', 'v3', developerKey=os.getenv('YOUTUBE_API_KEY'))

def save_crawls():
    # Path to the folder containing the CSV files
    cwd = os.getcwd()
    folder_path = os.path.join(cwd, 'setup/crawls')

    # Get a list of all CSV files in the folder
    csv_files = [file for file in os.listdir(folder_path) if file.endswith('.csv')]

    # Create an empty DataFrame to store the cumulative data
    cumulative_df = pd.DataFrame()

    # Iterate over each CSV file
    for i, file in enumerate(csv_files):
        # Read the CSV file into a DataFrame
        df = pd.read_csv(os.path.join(folder_path, file))
        df['fileNumber'] = i + 1
        
        # Append the data from the current file to the cumulative DataFrame
        cumulative_df = pd.concat([cumulative_df, df], axis=0, ignore_index=True)

    # Path to save the cumulative CSV file
    output_path = os.path.join(folder_path, 'cumulative.csv')

    # Save the cumulative DataFrame as a CSV file
    cumulative_df.to_csv(output_path, index=False)

def load_crawls():
    if os.path.exists('setup/crawls/cumulative.csv'):
        df = pd.read_csv('setup/crawls/cumulative.csv')
        return df

def fetch_video_details(video_ids):
    # Make an API call to the YouTube API to fetch information about the video
    response = YOUTUBE.videos().list(
        part="snippet,contentDetails",
        id=video_ids
    ).execute()

   #Extract duration and description from response
    descriptions = []
    durations = []
    for item in response["items"]:
        description = item["snippet"]["description"]
        descriptions.append(description)
        duration = item["contentDetails"]["duration"]
        durations.append(duration)

    return descriptions, durations

def add_video_details(df):
    # Fetch details for each video ID and add to dataframe
    descriptions = []
    durations = []

    #make batches of 50 video ids
    video_ids = df["videoId"].tolist()
    video_id_batches = [video_ids[i:i + 50] for i in range(0, len(video_ids), 50)]

    #fetch details for each batch
    for batch in tqdm(video_id_batches):
        description, duration = fetch_video_details(batch)
        descriptions.extend(description)
        durations.extend(duration)

    df["full_description"] = descriptions
    df["duration"] = durations

    #shorten description to 200 characters
    df["description"] = df["full_description"].str.slice(stop=200)

def save_cumulative(df):
    #save to cumulative.csv
    df.to_csv('setup/crawls/cumulative.csv', index=False)

def load_df():
    #load cumulative.csv
    df = pd.read_csv('setup/crawls/modified_dataframe.csv')
    return df

def parse_gpt_choice(choice: dict) -> dict:
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

def evaluate(row):
    #extract relevant information from row
    title = row["title"]
    description = row["description_400"]
    channelTitle = row["channelTitle"]
    politician = row["politician"]

    content_filter_prompt = f"""You are a research analyst, interested in gathering footage of {politician} speaking. You will be given a video to evaluate. Your goal is to determine whether the content is good enough for your research. You only want to see content where the politician is the primary speaker.

    First, describe the reasons why {politician} may or may not be the primary speaker in the video. Then, answer the following question: is {politician} is the primary speaker in the video? (y/n). Always return your evaluation as a single JSON object, enclosed in curly brakets. For example:
        
    % Example %
    Title: {politician} speaks at [event]
    Description: {politician} addresses the crowd at [event]
    Channel Title: {politician} News Network
    Published At: 2021-01-01
    {{"reasoning": "This video is not permissible because it is a news clip about {politician}, not a speech by {politician}.", "primary": "y"}}

    % Your Response %
    Title: {title}
    Description: {description}
    Channel Title: {channelTitle}"""

    # create openAI endpoint
    result = openai.Completion.create(
        model="gpt-3.5-turbo-instruct",
        prompt=content_filter_prompt,
        max_tokens=1000,
        n=3
    )

    choices = result['choices']
    json_responses = [ parse_gpt_choice(choice) for choice in choices ]

    votes = [ json.get('primary', None) for json in json_responses ]
    reasons = [ json.get('reasoning', None) for json in json_responses ]

    num_yes = votes.count('y')
    num_no = votes.count('n')
    is_permissible = num_yes > num_no

    return is_permissible
    
if __name__ == "__main__":
    # Load the modified crawl list
    df = pd.read_csv('setup/crawls/cleaned.csv')
    # Iterate over each row in the DataFrame
    # Apply evalution function to each row
    # Add the results as a new column in the DataFrame
    tqdm.pandas(total=df.shape[0])
    df['permissible'] = df.progress_apply(lambda row: evaluate(row), axis=1)
    # Save the DataFrame as a CSV file
    df.to_csv('setup/crawls/cleaned_dataframe.csv', index=False)


