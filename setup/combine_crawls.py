import pandas as pd
import os

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

if __name__ == '__main__':
    # Path to the folder containing the CSV files
    cwd = os.getcwd()
    folder_path = os.path.join(cwd, 'setup/crawls')

    # Get a list of all CSV files in the folder
    csv_files = [file for file in os.listdir(folder_path) if file.endswith('.csv')]

    # Sort the files by name
    csv_files.sort()
    print(csv_files)
    
    # Get all search queries
    query_mat = [
        get_search_queries(politician) for politician in POLITICIANS
    ]
    n_queries_per_politician = len(query_mat[0])

    # Flatten list
    politician_iterable = [ politician for politician in POLITICIANS for i in range(n_queries_per_politician) ]

    iterable = list(zip(politician_iterable, csv_files))

    # Create an empty DataFrame to store the cumulative data
    cumulative_df = pd.DataFrame()

    # Iterate over each CSV file
    for politician, file in iterable:
        # Read the CSV file into a DataFrame
        df = pd.read_csv(os.path.join(folder_path, file))
        df['politician'] = politician
        
        # Append the data from the current file to the cumulative DataFrame
        cumulative_df = pd.concat([cumulative_df, df], axis=0, ignore_index=True)

    # Path to save the cumulative CSV file
    output_path = os.path.join(folder_path, 'cumulative.csv')

    # Save the cumulative DataFrame as a CSV file
    cumulative_df.to_csv(output_path, index=False)