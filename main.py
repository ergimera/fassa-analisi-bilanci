import streamlit as st
import os
import pandas as pd
from openai import OpenAI
import openai
import time
from datetime import datetime

openai.organization = "org-ZCInae5ZEKOe41iOgJqcI0i1"
openai.api_key = "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"

client = OpenAI(
  api_key=openai.api_key,  # this is also the default, it can be omitted
)

def process_question(file_path, question, assistantid, client):
    # Create the file object
    with open(file_path, "rb") as file_data:
        file = client.files.create(
            file=file_data,
            purpose='assistants'
        )
        file_id = file.id

    # Create thread message
    thread = client.beta.threads.create(
        messages=[
            {
                "role": "user",
                "content": question,
                "file_ids": [file_id]
            }
        ]
    )
    thread_id = thread.id

    # Execute the run
    run = client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=assistantid,
        model="gpt-4-1106-preview",
        tools=[{"type": "code_interpreter"}, {"type": "retrieval"}]
    )
    run_id = run.id

    # Retrieve the run
    retrieved_run = client.beta.threads.runs.retrieve(
        thread_id=thread_id,
        run_id=run_id
    )

    # Wait for the run to complete
    while True:
        run = client.beta.threads.runs.retrieve(
            thread_id=thread_id,
            run_id=run_id
        )
        if run.status == "completed":
            break
        time.sleep(3)  # Wait for 3 seconds before checking again

    # Retrieve thread messages
    thread_messages = client.beta.threads.messages.list(thread_id)
    message_id = thread_messages.first_id  # Need to verify the attribute name for the first message ID

    # Retrieve the message object
    message = client.beta.threads.messages.retrieve(
        thread_id=thread_id,
        message_id=message_id
    )

    # Presuming that message.content is a list with text and annotations attributes
    message_content = message.content[0].text
    client.files.delete(file.id)

    return message_content.value

def process_all_pdfs_to_dataframe(directory_path, question, assistantid, client):
    results = []
    for filename in os.listdir(directory_path):
        if filename.endswith(".pdf"):
            file_path = os.path.join(directory_path, filename)
            try:
                response = process_question(file_path, question, assistantid, client)
                results.append({
                    "File": filename,
                    "Question": question,
                    "Response": response
                })
            except Exception as e:
                print(f"An error occurred while processing {filename}: {e}")
                results.append({
                    "Società": filename,
                    "Domanda": question,
                    "Risposta": "Error: " + str(e)
                })
    return pd.DataFrame(results)


# Streamlit app code
st.title('Analisi PDF Bilanci 📒')

# Define a function to return a string containing the CSS to set the background image
def get_background_image_css(image_url):
    return f"""
    <style>
    .stApp {{
        background-image: url("{image_url}");
        background-size: cover;
    }}
    </style>
    """

# Set the URL of your background image
background_image_url = 'https://i.ibb.co/r0tQHff/164506-dark-blue-texture-background-design-2.jpg'

# Call the function to get the CSS style string
css_style = get_background_image_css(background_image_url)

# Inject custom CSS with the background image into the Streamlit app
st.markdown(css_style, unsafe_allow_html=True)


directory_path = st.text_input('Seleziona la cartella contentente i bilanci', '')
question = st.text_area('Inserisci la domanda da porre', 'Sarebbe possibile ottenere un elenco dettagliato della distribuzione dei ricavi, suddiviso per categorie di attività? Vorrei avere informazioni più specifiche su come i ricavi sono ripartiti tra le varie attività o settori')
assistant_id = st.text_input("Indicare l'Assistant ID", 'asst_tH6OUSI6c6QAS4eXwBnG80a0')

# Function to get the current date and time
def get_current_date_time():
    return datetime.now()

# Function to format date and time into a string suitable for a file name
def format_date_time(date_time):
    return date_time.strftime('%Y_%m_%d_%H-%M-%S')

# Function to concatenate file name components
def concatenate_file_name(base_name, date_time_str, extension):
    return f"{base_name}_{date_time_str}{extension}"

# Function to combine directory path and file name
def combine_path(directory_path, file_name):
    return os.path.join(directory_path, file_name)

current_datetime = get_current_date_time()
formatted_datetime = format_date_time(current_datetime)
file_name = concatenate_file_name('responses', formatted_datetime, '.xlsx')
full_path = combine_path(directory_path, file_name)


if st.button('Process PDFs'):
    if directory_path and question and assistant_id:
        try:
            with st.spinner('Processing...'):
                df_responses = process_all_pdfs_to_dataframe(directory_path, question, assistant_id, client)
            st.dataframe(df_responses)
            excel_path = full_path
            df_responses.to_excel(excel_path, index=False)
            st.success(f'Results saved to {excel_path}')
        except Exception as e:
            st.error(f'An error occurred: {e}')
    else:
        st.error('Please fill out all fields before processing.')
