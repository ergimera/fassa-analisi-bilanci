import streamlit as st
import pandas as pd
import openai
from datetime import datetime
from openai import OpenAI

# Streamlit app code
st.title('Analisi PDF Bilanci 📒')

# Set the URL of your background image
background_image_url = 'https://i.ibb.co/r0tQHff/164506-dark-blue-texture-background-design-2.jpg'

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

# Call the function to get the CSS style string
css_style = get_background_image_css(background_image_url)

# Inject custom CSS with the background image into the Streamlit app
st.markdown(css_style, unsafe_allow_html=True)

question = st.text_area('Inserisci la domanda da porre', 'Sarebbe possibile ottenere un elenco dettagliato della distribuzione dei ricavi, suddiviso per categorie di attività? Vorrei avere informazioni più specifiche su come i ricavi sono ripartiti tra le varie attività o settori')
assistant_id = st.text_input("Indicare l'Assistant ID", 'asst_tH6OUSI6c6QAS4eXwBnG80a0')
api_key = st.text_input("Indicare Open AI Key")

openai.organization = "org-ZCInae5ZEKOe41iOgJqcI0i1"
openai.api_key = api_key

client = OpenAI(api_key=api_key)

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
    thread = client.assistants.create_and_run(
        model="davinci",
        documents=[file_id],
        user_question=question
    )
    
    # Store the thread information for later retrieval in Streamlit's session state
    return {'thread_id': thread.id, 'file_id': file_id, 'filename': file_object.name}

# Streamlit control for initiating PDF processing
if st.button('Process PDFs'):
    if uploaded_files and question and assistant_id and api_key:
        # Initialize an empty list to store responses for each file
        pending_runs = []
        
        # Update client with the provided API key
        openai.api_key = api_key
        client = OpenAI(api_key=openai.api_key)
        
        # Process each file and store pending runs information
        for uploaded_file in uploaded_files:
            if uploaded_file.name.endswith(".pdf"):
                run_info = process_question(uploaded_file, question, assistant_id, client)
                if run_info is not None:
                    pending_runs.append(run_info)
        
        # Check if there are any pending runs to process
        if pending_runs:
            # Store the list of pending runs in the session state
            st.session_state['pending_runs'] = pending_runs
            st.session_state['results'] = []
            # Indicate to the user that files are being processed
            st.success('Processing started. Click on "Check Status" to get updates.')
        else:
            st.error('No valid PDF files found. Please upload PDF files and try again.')
    else:
        st.error('Please fill out all fields and upload at least one PDF file before processing.')

# Define a function that checks the status of a pending run and retrieves the results
def check_status_and_get_results():
    if 'pending_runs' in st.session_state:
        for run_info in st.session_state['pending_runs']:
            if 'response' not in run_info:
                # Grab the status/response of the run with OpenAI's retrieve API call
                response = client.assistants.retrieve(run_info['thread_id'])
                if response['status'] == 'succeeded':
                    run_info['response'] = response['answers'][0]['text']
                    st.session_state['results'].append(run_info)
                # The else case is implicit and we just wait more

# Streamlit control for checking the status of PDF processing
if st.button('Check Status'):
    check_status_and_get_results()
    if not st.session_state['pending_runs']:
        st.success('All files have been processed.')
        # Convert the results to a DataFrame and display it
        df_results = pd.DataFrame(st.session_state['results'])
        st.dataframe(df_results)
        # Generate an Excel file from the DataFrame
        current_datetime = datetime.now().strftime('%Y_%m_%d_%H_%M_%S')
        filename = f'responses_{current_datetime}.xlsx'
        df_results.to_excel(filename, index=False)
        with open(filename, 'rb') as f:
            st.download_button(
                label='Download Excel file',
                data=f,
                file_name=filename,
                mime='application/vnd.ms-excel'
            )
    else:
        st.info('Some files are still processing, please check back later.')
