# import asyncio
import pinecone
import os
import streamlit as st
from politicians import POLITICIANS
from chain import Chain, Profile
import re
import base64
import time
from utils import extract_video_link_and_start_time

def display_message(response: dict, stream_response: bool = False) -> int:
    "returns elapsed time to display message"
    #autoplay audio and stream reponse in approx same time.
    def display_transcription(output_text: str, elapsed_time: int=30, placeholder=None) -> str:
        if placeholder is None:
            placeholder = st.empty()
        full_response = ''
        placeholder.markdown(full_response)
        # Simulate stream of response with milliseconds delay
        split = output_text.split()
        nchunks = len(split)
        interval = elapsed_time / nchunks
        for chunk in split:
            full_response += chunk + " "
            time.sleep(interval)
            # Add a blinking cursor to simulate typding
            placeholder.markdown(full_response + "▌")
        placeholder.markdown(full_response)
        return full_response

    def display_audio(audio: bytes, placeholder=None):
        if placeholder is None:
            placeholder = st.empty()
        audio_base64 = base64.b64encode(audio).decode('utf-8')
        audio_tag = f'<audio controls src="data:audio/wav;base64,{audio_base64}">'
        placeholder.markdown(audio_tag, unsafe_allow_html=True)
    
    def autoplay_audio(file_path: str = None, data: bytes = None, display_player: bool = True):
        if data is not None:
            audio_base64 = base64.b64encode(data).decode('utf-8')
            audio_tag = f'<audio {"controls " if display_player else "" }autoplay="true" src="data:audio/wav;base64,{audio_base64}">'

        elif file_path is not None:
            with open(file_path, "rb") as f:
                data = f.read()
                b64 = base64.b64encode(data).decode()
                audio_tag = f"""
                    <audio {"controls " if display_player else "" }autoplay="true">
                    <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
                    </audio>
                    """
    
        st.markdown(audio_tag, unsafe_allow_html=True)

    def get_audio_length(audio: bytes) -> int:
        bit_rate = 128000
        length = len(audio) / bit_rate * 8
        return int(length)

    def display_citations(citations, placeholder=None):
        if len(citations) == 0:
            return
        if placeholder is None:
            placeholder = st.empty()
        references, links = citations
        # convert references to references in string format
        references = [str(reference) for reference in references]
        tabs = placeholder.tabs(references)
        for tab, reference, link in zip(tabs, references, links):
            video_link, start_time = extract_video_link_and_start_time(link)
            with tab:
                st.video(video_link, start_time=start_time)

    # Extract audio response from response dict
    #TODO: implement audio response
    # audio_response = response["audio"]
    with open("test.wav", "rb") as f:
        audio_response = f.read()

    name = response.get('role', None)
    avatar = response.get('avatar', None)
    
    with st.chat_message(name=name, avatar=avatar):

        if name == "user" or name == "Molus":
            st.markdown(response["content"])
            return

        shortcode = response.get('shortcode', None)
        header = f"**{name}** @{shortcode}"
        st.markdown(header)

        # Extract transcribed response from response dict
        assistant_response = response.get('content', None)
        elapsed_time = 0

        if stream_response:
            stream_time = get_audio_length(audio_response)
            transcribe_time = 3
            # autoplay audio response
            autoplay_audio(data=audio_response, display_player=True)
            # Stream transcribed response at same time as audio
            display_transcription(assistant_response, elapsed_time=transcribe_time)
            elapsed_time = stream_time - transcribe_time
        else:
            display_audio(audio_response)
            st.markdown(assistant_response)

        citations = response.get('citations', None)
        display_citations(citations)

        return elapsed_time

def run_and_display_chain(chain: Chain):
    """
    call to debate.next_message()
    streamout the next available message
    append the next message to debate manager
    repeat until debate is over
    """
    #TODO: implement timeout we don't display two messages at once
    responses = []
    profile = chain.get_start()
    time_to_display = 0
    prev_display_time = 0
    while profile:
        response = profile.get_response()
        curr_time = time.time()
        if curr_time - prev_display_time < time_to_display:
            time.sleep(time_to_display - (curr_time - prev_display_time))
        time_to_display = display_message(response, stream_response=True)
        prev_display_time = time.time()
        responses.append(response)
        profile = chain.next_profile()

    st.session_state.messages.extend(responses)

USER_PROFILE_PIC = '🫨'
pinecone.init(
    api_key=os.environ.get('PINECONE_API_KEY'),
    environment=os.environ.get('PINECONE_ENV')
)
INDEX = pinecone.Index('v1')

#session state initialization
if "messages" not in st.session_state:
    politician_names = list(POLITICIANS.keys())
    politician_names.sort()
    #display message with politician names, images, and shortcodes
    politician_info = [f"- {p}, @**{POLITICIANS[p]['shortcode']}**" for p in politician_names ]
    names_and_shortcodes = "\n".join(politician_info)

    intro=f"""'@' the politicians below and ask them questions (or demand answers😉)\n\n{names_and_shortcodes}\n\nYou can chat with individuals or setup interactions. The will always talk in the order they are '@'ed.\n\nExample usage:\n - @gw how do you feel about the "Big Gretch" nickname?\n- @dt @jb @dt @jb debate the merits of the 2022 election: was it stolen?\n- @aoc @aoc @aoc rap the green new deal to me.\n- @mtg @jdv @vr @mtg @jdv @vr tell me why you should be the future of the republican party\n- @bo if you ran for public office again, what position would it be?
    """

    init_message = {
        "role": "Molus",
        "avatar": "🔺",
        "content": intro
    }
    st.session_state.messages = [
        init_message
    ]

if __name__ == "__main__":

    st.title("Molus🔺")

    # Display chat history
    for message in st.session_state.messages:
        display_message(message)

    if prompt := st.chat_input('Ask them anything...'):

        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt, 'avatar': USER_PROFILE_PIC})
        # Display user message in chat message container
        with st.chat_message("user", avatar=USER_PROFILE_PIC):
            st.markdown(prompt)

        # Extract chain in format "@dt @jb @oc @av"
        mentions = re.findall(r"@(\w+)", prompt)
        # Extract the instructions from the prompt
        prompt = re.sub(r"@(\w+)", "", prompt).strip()

        if len(mentions) > 0 and prompt != "":

            #TODO add error handling for invalid shortcode
            profiles = [ Profile(index=INDEX, shortcode=code) for code in mentions ]

            # create chain from the profiles and prompt
            chain = Chain(
                profiles=profiles,
                prompt=prompt
            )

            # run the chain and display the results
            run_and_display_chain(chain)
        
        else:
            st.error("Please '@' a politician to ask them a question or setup an interaction.")
            st.stop()