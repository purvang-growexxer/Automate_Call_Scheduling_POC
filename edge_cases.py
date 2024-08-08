import os
import re
import time
from datetime import datetime, timedelta
import configparser
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from langchain_groq import ChatGroq

SCOPES = ["https://www.googleapis.com/auth/calendar"]

def extract_meeting_info(user_input, max_retries=3):
    """Extracts meeting information from user input using LLM."""
    llm_prompt = f"""
    Extract the following meeting details from the input: '{user_input}'.
    Use zeel.gudhka@growexx.com as the default host if the host's email address is not specified in the input.
    If the input has no information about start_date, start_time, end_date, end_time, or attendees, then leave those values as blank. Do not assume anything on your own.
        
    Required details:
    - summary: Meeting Summary (if not provided)
    - location: Any Location (if not provided)
    - description: Meeting Description (if not provided)
    - start_date: (format YYYY-MM-DD, interpret relative dates like today, tomorrow, next Monday)
    - start_time: (format HH:MM)
    - end_date: (format YYYY-MM-DD, interpret relative dates like today, tomorrow, next Monday)
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
    """
    
    attempt = 0
    while attempt < max_retries:
        try:
            config = configparser.ConfigParser()
            config.read('API.ini')
            API_key = config['api'].get('api_key')
            llm = ChatGroq(model="llama-3.1-70b-versatile", temperature=0.2, groq_api_key=API_key)
            llm_response = llm.invoke(llm_prompt)
            break
        except Exception as e:
            attempt += 1
            if attempt >= max_retries:
                print(f"An error occurred while processing the LLM request: {e}")
                return None
            time.sleep(2 ** attempt)
    
    llm_output = llm_response.content.strip()
    llm_data = {}
    for line in llm_output.split('\n'):
        if not line.strip():
            continue
        try:
            key, value = line.strip().split(':', 1)
            llm_data[key.strip().lower()] = value.strip()
        except ValueError:
            print(f"Error parsing LLM response line: {line}")

    if 'attendees' in llm_data:
        llm_data['attendees'] = ', '.join(attendee.strip() for attendee in llm_data['attendees'].split(','))
    return llm_data

def get_current_date():
    return datetime.now()

def validate_meeting_details(details):
    details.setdefault('summary', 'Meeting Summary')
    details.setdefault('location', 'Any Location')
    details.setdefault('description', 'Meeting Description')
    details.setdefault('start_date', get_current_date().strftime('%Y-%m-%d'))

    if not details.get('end_date'):
        details['end_date'] = details['start_date']
    details.setdefault('time_zone', 'Asia/Kolkata')
    details.setdefault('recurrence', 'RRULE:FREQ=DAILY;COUNT=1')
    details.setdefault('conference_data', 'yes')

    if 'start_time' not in details or not details['start_time']:
        details['start_time'] = None

    if 'end_time' not in details or not details['end_time']:
        details['end_time'] = None

    try:
        datetime.strptime(details['start_date'], '%Y-%m-%d')
        datetime.strptime(details['end_date'], '%Y-%m-%d')
    except ValueError:
        raise ValueError("Invalid date format. Please use YYYY-MM-DD.")

    if 'attendees' in details and isinstance(details['attendees'], str):
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
    if 'end_time' not in details or not details['end_time']:
        details['end_time'] = input("Please provide the end time (HH:MM): ").strip()
    if len([attendee for attendee in details['attendees'] if attendee != 'zeel.gudhka@growexx.com']) < 1:
        other_attendees = input("Please provide the attendees' emails (comma-separated, excluding the host): ").strip()
        details['attendees'].extend([email.strip() for email in other_attendees.split(',')])
        if 'zeel.gudhka@growexx.com' not in details['attendees']:
            details['attendees'].append('zeel.gudhka@growexx.com')
    return details

def is_valid_date(date_str):
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False

def adjust_date_for_financial_year(date_str):
    today = get_current_date()
    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    
    print(f"Original date: {date_obj}")  # Debugging statement

    if date_obj.month < 4 and today.month >= 8:  # If date is before April and today is after July
        try:
            date_obj = date_obj.replace(year=date_obj.year + 1)
        except ValueError:
            print(f"Invalid date adjustment for non-leap year: {date_obj}")
            return None
    
    return date_obj.strftime('%Y-%m-%d')

def create_google_meet_event(service, meeting_details):
    event = {
        'summary': meeting_details['summary'],
        'location': meeting_details['location'],
        'description': meeting_details['description'],
        'start': {
            'dateTime': f"{meeting_details['start_date']}T{meeting_details['start_time']}:00",
            'timeZone': meeting_details['time_zone'],
        },
        'end': {
            'dateTime': f"{meeting_details['end_date']}T{meeting_details['end_time']}:00",
            'timeZone': meeting_details['time_zone'],
        },
        'recurrence': [
            meeting_details['recurrence']
        ],
        'attendees': [{'email': email} for email in meeting_details['attendees']],
        'conferenceData': {
            'createRequest': {
                'requestId': f"{datetime.now().timestamp()}"
            }
        },
        'reminders': {
            'useDefault': False,
            'overrides': [
                {'method': 'email', 'minutes': 24 * 60},
                {'method': 'popup', 'minutes': 10},
            ],
        },
    }

    if meeting_details['conference_data'].lower() == 'yes':
        event['conferenceDataVersion'] = 1

    event_result = service.events().insert(calendarId='primary', body=event, conferenceDataVersion=1).execute()
    return event_result

def main():
    try:
        creds = None
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            with open('token.json', 'w') as token:
                token.write(creds.to_json())

        service = build('calendar', 'v3', credentials=creds)
        
        user_input = input("Enter your meeting request: ").strip()
        meeting_details = extract_meeting_info(user_input)
        if not meeting_details:
            return
        meeting_details = validate_meeting_details(meeting_details)
        meeting_details = prompt_for_missing_details(meeting_details)
        
        # Adjust start and end dates for the financial year format
        meeting_details['start_date'] = adjust_date_for_financial_year(meeting_details['start_date'])
        if not meeting_details['start_date']:
            print("The provided start date is invalid for the specified year.")
            return

        meeting_details['end_date'] = adjust_date_for_financial_year(meeting_details['end_date'])
        if not meeting_details['end_date']:
            print("The provided end date is invalid for the specified year.")
            return

        event = create_google_meet_event(service, meeting_details)
        print(f"Event created: {event['htmlLink']}")

    except HttpError as error:
        print(f"An error occurred: {error}")

if __name__ == "__main__":
    main()