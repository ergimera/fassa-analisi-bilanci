import streamlit as st
import os
import pandas as pd
from openai import OpenAI
import openai
from datetime import datetime

# Streamlit app code
st.title('Analisi PDF Bilanci 📒')

question = st.text_area('Inserisci la domanda da porre', 'Sarebbe possibile ottenere un elenco dettagliato della distribuzione dei ricavi, suddiviso per categorie di attività? Vorrei avere informazioni più specifiche su come i ricavi sono ripartiti tra le varie attività o settori')
assistant_id = st.text_input("Indicare l'Assistant ID", 'asst_tH6OUSI6c6QAS4eXwBnG80a0')
api_key = st.text_input("Indicare Open AI Key")

openai.organization = "org-ZCInae5ZEKOe41iOgJqcI0i1"
openai.api_key = api_key

client = OpenAI(
  api_key=openai.api_key,  # this is also the default, it can be omitted
)

uploaded_files = st.file_uploader(
    "Seleziona i bilanci PDF da analizzare", 
    type="pdf", 
    accept_multiple_files=True
)


def process_question(file_object, question, assistantid, client):
    # Create the file object
    file = client.files.create(
        file=file_object,
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
    
    # Initialize or update session state for run status
    if 'run_status' not in st.session_state:
        st.session_state['run_status'] = 'not started'

    # Define a function to check the run status
    def check_run_status():
        if 'last_check' not in st.session_state or (datetime.now() - st.session_state['last_check']).seconds > 3:
            run = client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run_id
            )
            # Update the session state with the latest status
            st.session_state['run_status'] = run.status
            # Update the last checked timestamp
            st.session_state['last_check'] = datetime.now()
        return st.session_state['run_status']

    # Check the current run status
    current_status = check_run_status()

    # If the run is completed, get the resulting message
    if current_status == "completed":
        # Retrieve thread messages
        thread_messages = client.beta.threads.messages.list(thread_id)
        message_id = thread_messages.first_id  # Verify the attribute name for the first message ID
        
        # Retrieve the message object
        message = client.beta.threads.messages.retrieve(
            thread_id=thread_id,
            message_id=message_id
        )
        
        # Presuming that message.content is structured with text and annotations
        message_content = message.content[0].text
        
        # Delete the uploaded file
        client.files.delete(file_id)
        
        # Return the message content as the function output
        return message_content
    else:
        # Prompt the user to check back later for the result
        st.info('Processing... Please check back in a moment by pressing "Check Status".')
        return None  # Indicates that the run is not completed yet

def process_all_pdfs_to_dataframe(uploaded_files, question, assistantid, client):
    # Initialize the results list
    results = []

    # Loop through each uploaded file object
    for uploaded_file in uploaded_files:
        if uploaded_file.name.endswith(".pdf"):
            # Process the uploaded file
            response = process_question(uploaded_file, question, assistantid, client)

            # Since processing is asynchronous, we may not receive the response immediately
            if response is not None:
                # We have a response; append to the results list
                results.append({
                    "File": uploaded_file.name,
                    "Question": question,
                    "Response": response
                })
            else:
                # The response is not ready; append a placeholder indicating processing status
                results.append({
                    "File": uploaded_file.name,
                    "Question": question,
                    "Response": "Processing..."
                })

    # Convert the results list into a pandas DataFrame
    df_results = pd.DataFrame(results)

    # Return the DataFrame
    return df_results




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


# Streamlit control for initiating PDF processing
if st.button('Process PDFs'):
    if uploaded_files and question and assistant_id and api_key:
        client = OpenAI(api_key=api_key)
        with st.spinner('Processing...'):
            df_responses = process_all_pdfs_to_dataframe(uploaded_files, question, assistant_id, client)
            st.dataframe(df_responses)
            # Save responses to an Excel sheet
            current_datetime = datetime.now().strftime('%Y_%m_%d_%H-%M-%S')
            file_name = f'responses_{current_datetime}.xlsx'
            df_responses.to_excel(file_name, index=False)
            st.success(f'Results saved to {file_name}')
            # Provide a download link for the Excel file
            with open(file_name, "rb") as file:
                st.download_button(
                    label="Download Excel file",
                    data=file,
                    file_name=file_name,
                    mime="application/vnd.ms-excel"
                )
    else:
        st.error('Please fill out all fields and upload at least one PDF file before processing.')

# Rerun the app to update the status of the processing
if st.button('Check Status'):
    st.experimental_rerun()
