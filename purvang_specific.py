import os.path
from datetime import datetime, timedelta
import re
import pytz
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from langchain_groq import ChatGroq
import configparser
 
SCOPES = ["https://www.googleapis.com/auth/calendar"]
 
def get_current_date():
    return datetime.now().date()
 
def extract_meeting_info(user_input):
    """Extracts meeting information from user input using LLM."""
    llm_prompt = f"""
    Extract the following meeting details from the input: '{user_input}'.
 
    Required details:
    - summary: Meeting Summary (if not provided)
    - location: Any Location (if not provided)
    - description: Meeting Description (if not provided)
    - start_date: (format YYYY-MM-DD, interpret relative dates like today, tomorrow, next Monday)
    - start_time: (format HH:MM)
    - end_date: (format YYYY-MM-DD)
    - end_time: (format HH:MM)
    - time_zone: (default to IST if not provided)
    - recurrence: (default to "RRULE:FREQ=DAILY;COUNT=1" if not provided)
    - attendees: (comma-separated emails including the user)
    - conference_data: (yes/no, default to yes)
 
    Consider the current date as {datetime.now().strftime('%Y-%m-%d')}.
 
    Return the details in the following format:
    summary: <summary>
    location: <location>
    description: <description>
    start_date: <start_date>
    start_time: <start_time>
    end_date: <end_date>
    end_time: <end_time>
    time_zone: <time_zone>
    recurrence: <recurrence>
    attendees: <attendees>
    conference_data: <conference_data>
    If the user does not provide any end_time then set the meeting for 1 hour.
    """
 
    try:
        config = configparser.ConfigParser()
        config.read('API.ini')

        API_key = config['api']['api_key']
        llm = ChatGroq(model="llama-3.1-70b-versatile", temperature=0.2, groq_api_key=API_key)
        llm_response = llm.invoke(llm_prompt)
    except groq.InternalServerError as e:
        print(f"An error occurred while processing the LLM request: {e}")
        return None
 
    llm_output = llm_response.content.strip()
    llm_data = {}
    for line in llm_output.split('\n'):
        if not line.strip():  # Skip empty lines
            continue
        try:
            key, value = line.strip().split(':', 1)
            llm_data[key.strip().lower()] = value.strip()
        except ValueError:
            print(f"Error parsing LLM response line: {line}")  # Log unexpected line
 
    return llm_data
 
def validate_meeting_details(details):
    # Set default values if keys are missing
    details.setdefault('summary', 'Meeting Summary')
    details.setdefault('location', 'Any Location')
    details.setdefault('description', 'Meeting Description')
    details.setdefault('start_date', get_current_date().strftime('%Y-%m-%d'))
    details.setdefault('end_date', details['start_date'])
    details.setdefault('time_zone', 'Asia/Kolkata')
    details.setdefault('recurrence', 'RRULE:FREQ=DAILY;COUNT=1')
    details.setdefault('conference_data', 'yes')
 
    # Parse start and end times
    if 'start_time' not in details or not details['start_time']:
        details['start_time'] = '09:00'  # Default start time
    if 'end_time' not in details or not details['end_time']:
        # Default to 1 hour meeting if end time is not provided
        start_dt = datetime.strptime(details['start_time'], '%H:%M')
        end_dt = start_dt + timedelta(hours=1)
        details['end_time'] = end_dt.strftime('%H:%M')
 
    # Ensure start_date and end_date are in correct format
    try:
        datetime.strptime(details['start_date'], '%Y-%m-%d')
        datetime.strptime(details['end_date'], '%Y-%m-%d')
    except ValueError:
        raise ValueError("Invalid date format. Please use YYYY-MM-DD.")
 
    # Validate attendees
    if 'attendees' in details:
        valid_emails = []
        for email in details['attendees'].split(","):
            email = email.strip()
            if re.match(r"[^@]+@[^@]+\.[^@]+", email):
                valid_emails.append(email)
            else:
                print(f"Invalid email address skipped: {email}")
        details['attendees'] = valid_emails
 
    return details
 
def prompt_for_missing_details(details):
    if 'start_date' not in details or not details['start_date']:
        details['start_date'] = input("Please provide the start date (YYYY-MM-DD): ").strip()
    if 'start_time' not in details or not details['start_time']:
        details['start_time'] = input("Please provide the start time (HH:MM): ").strip()
    if 'attendees' not in details or not details['attendees']:
        details['attendees'] = input("Please provide the attendees' emails (comma-separated): ").strip().split(',')
 
    return details
 
def create_google_meet_event(service, meeting_details):
    start_datetime = f"{meeting_details['start_date']}T{meeting_details['start_time']}:00"
    end_datetime = f"{meeting_details['end_date']}T{meeting_details['end_time']}:00"
 
    attendees = [{"email": email} for email in meeting_details['attendees']]
 
    event = {
        "summary": meeting_details["summary"],
        "location": meeting_details["location"],
        "description": meeting_details["description"],
        "colorId": 6,
        "start": {
            "dateTime": start_datetime,
            "timeZone": meeting_details["time_zone"]
        },
        "end": {
            "dateTime": end_datetime,
            "timeZone": meeting_details["time_zone"]
        },
        "recurrence": [
            meeting_details["recurrence"]
        ],
        "attendees": attendees,
        "conferenceData": {
            "createRequest": {
                "requestId": "sample123",
                "conferenceSolutionKey": {
                    "type": "hangoutsMeet"
                }
            }
        } if meeting_details["conference_data"].lower() == 'yes' else {}
    }
 
    event = service.events().insert(calendarId="primary", body=event, conferenceDataVersion=1).execute()
 
    return event
 
def main():
    creds = None
 
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
 
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
 
        with open("token.json", "w") as token:
            token.write(creds.to_json())
 
    try:
        service = build("calendar", "v3", credentials=creds)
 
        user_input = input("Enter your meeting request: ")
        meeting_details = extract_meeting_info(user_input)
        if meeting_details is None:
            print("Failed to extract meeting details from the input.")
            return
 
        meeting_details = validate_meeting_details(meeting_details)
        meeting_details = prompt_for_missing_details(meeting_details)
 
        event = create_google_meet_event(service, meeting_details)
 
        print(f"Event created: {event.get('htmlLink')}")
    except HttpError as error:
        print(f"An error occurred: {error}")
    except ValueError as ve:
        print(f"Validation error: {ve}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
 
if __name__ == "__main__":
    main()