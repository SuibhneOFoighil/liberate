import asyncio
import streamlit as st
from politicians import POLITICIANS
from debate import Debater, Debate

def display_message(message: dict):
    with st.chat_message(message["role"], avatar=message.get('avatar', None)):
        if message["role"] == "assistant":
            # display_audio(message["audio"])
            st.markdown(message["content"])
            # display_citations(message["citations"])
        else:
            st.markdown(message["content"])

async def display_response(response: dict):
    await asyncio.sleep(30)
    return f"other_{input_value}"

def display_debate(debate: Debate):
    """
    Async call to debate.next_message()
    streamout the next available message
    append the next message to debate manager
    repeat until debate is over
    """

    Nrounds = debate.Nrounds
    prev_response = None
    for i in range(Nrounds * 2):
        promise = asyncio.ensure_future(debate.next_message())
        if prev_response:
            await display_response(prev_response)
        model_response = await promise
        prev_response = model_response



politician_names = list(POLITICIANS.keys())

st.title("Molus🔺")
config, debate = st.tabs(["Configuration", "Debate"])

with config:
    left, right = st.columns(2)
    with left:
        first_debater = st.selectbox("1st Debater", politician_names)
        selection = st.selectbox("Style", ["Custom", "Formal", "Informal"], key="style1")
        first_debater_style = st.text_area("Prompt", key="custom1")
       
    with right:
        second_debater = st.selectbox("2nd Debater", politician_names)
        selection = st.selectbox("Style", ["Custom", "Formal", "Informal"], key="style2")
        second_debater_style = st.text_area("Prompt", key="custom2")
        

with debate:
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display prompt input
    left, right = st.columns(2)
    with left:
        debate_preset = st.selectbox("Topic", ["Custom", "Formal", "Informal"], key="style")
    with right:
        Nrounds = st.number_input("Number of rounds", min_value=1, max_value=10, value=3, key="Nrounds")
    prompt = st.text_area(f"*{first_debater}* and *{second_debater}* debate...", key="prompt")
    run = st.button("Run", use_container_width=True)
    if run:
        st.balloons()
        Debater1 = Debater(first_debater, first_debater_style, POLITICIANS[first_debater]["avatar"])
        Debater2 = Debater(second_debater, second_debater_style, POLITICIANS[second_debater]["avatar"])
        debate = Debate(Debater1, Debater2, prompt, Nrounds)
        display_debate(debate)

        # Display chat history
        for message in st.session_state.messages:
            display_message(message)