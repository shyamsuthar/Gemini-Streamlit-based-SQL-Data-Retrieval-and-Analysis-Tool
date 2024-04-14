import streamlit as st
import pyodbc
import pandas as pd
import logging
import speech_recognition as sr
import google.generativeai as genai
from pygwalker.api.streamlit import init_streamlit_comm, get_streamlit_html
import streamlit.components.v1 as components

logging.basicConfig(level=logging.INFO)

genai.configure(api_key='your api key')

# Function to generate response using Generative AI model
def get_gemini_response(question):
    model = genai.GenerativeModel('gemini-pro')
    response = model.generate_content([question])
    return response.text

# Function to create SQLAlchemy engine for the selected database
def get_engine(server, database, username, password):
    try:
        connection_string = f'DRIVER=SQL Server;SERVER={server};DATABASE={database};UID={username};PWD={password}'
        connection = pyodbc.connect(connection_string)
        return connection, None
    except Exception as e:
        return None, f"Error connecting to the database: {str(e)}"

# Function to retrieve databases from the selected server
def get_databases(server, username, password):
    try:
        connection_string = f'DRIVER=SQL Server;SERVER={server};UID={username};PWD={password}'
        connection = pyodbc.connect(connection_string)
        cursor = connection.cursor()
        cursor.execute("SELECT name FROM sys.databases")
        databases = [db[0] for db in cursor.fetchall()]
        return databases, None
    except Exception as e:
        return None, f"Error retrieving databases: {str(e)}"

# Function to execute SQL query and return result as DataFrame
def execute_sql_query(connection, sql_query):
    try:
        result = pd.read_sql_query(sql_query, connection)
        return result, sql_query, None
    except Exception as e:
        return None, sql_query, f"Error executing SQL query: {str(e)}"

# Function to perform speech recognition
def perform_speech_recognition():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        st.write("Listening...")
        audio = recognizer.listen(source)
    try:
        spoken_question = recognizer.recognize_google(audio)
        return spoken_question
    except sr.UnknownValueError:
        st.warning("Google Speech Recognition could not understand audio. Please try again.")
        return ""
    except sr.RequestError as e:
        st.error(f"Could not request results from Google Speech Recognition service; {e}")
        return ""

# Function to generate HTML for PyGWalker visualization
def get_pyg_html(df: pd.DataFrame) -> str:
    html = get_streamlit_html(df, spec="./gw0.json", use_kernel_calc=True, debug=False)
    return html

# Streamlit App
def main():
    st.set_page_config(page_title="Retrieve Any SQL Query")
    st.header("Gemini App To Retrieve SQL Data")

    server = '172.31.14.154'  
    username = 'sa'
    password = 'KDataScience@7861'

    engine, connection_error = get_engine(server, 'master', username, password)
    if engine is None:
        st.error(connection_error)
        return

    databases, database_error = get_databases(server, username, password)
    if databases is None:
        st.error(database_error)
        return

    selected_database = st.selectbox("Select Database", databases)

    if selected_database:
        try:
            connection = engine  
            
            question = st.text_area("Ask Question")

            question_set_by_speech = False

            speech_recognition_button = st.button("Speak")
            if speech_recognition_button:
                spoken_question = perform_speech_recognition()
                if spoken_question:
                    question = spoken_question
                    st.text_area("Ask Question", value=question)
                    question_set_by_speech = True

            if question_set_by_speech:
                response = get_gemini_response(question)
                st.subheader("Generated Response:")
                st.write(response)
            else:
                generate_response_button = st.button("Generate Response")
                if generate_response_button and question.strip():
                    response = get_gemini_response(question)
                    st.subheader("Generated Response:")
                    st.write(response)

            sql_query = st.text_area("Enter SQL Query")

            if st.button("Retrieve Results") and sql_query:
                result, executed_query, query_error = execute_sql_query(connection, sql_query)

                if result is not None:
                    st.subheader("Executed SQL Query:")
                    st.code(executed_query)

                    st.subheader("SQL Query Result:")
                    st.dataframe(result)

                    if st.button("Generate Chart"):
                        # Here you can create charts based on the result DataFrame
                        # For example:
                        st.subheader("Example Chart")
                        st.bar_chart(result)

                    st.subheader("Exploratory Data Analysis Panel:")
                    components.html(get_pyg_html(result), width=1000, height=1000, scrolling=True)

                else:
                    st.warning("No results found.")
                    logging.warning("No results found for the SQL query.")
                    if query_error:
                        st.error(query_error)

        except Exception as e:
            st.error(f"Error connecting to the server or executing query: {str(e)}")
            logging.error(f"Error connecting to the server or executing query: {str(e)}")

if __name__ == "__main__":
    main()
