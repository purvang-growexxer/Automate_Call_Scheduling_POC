# import os.path
# from datetime import datetime, timedelta
# import re
# from google.auth.transport.requests import Request
# from google.oauth2.credentials import Credentials
# from google_auth_oauthlib.flow import InstalledAppFlow
# from googleapiclient.discovery import build
# from googleapiclient.errors import HttpError
# from langchain_groq import ChatGroq

# SCOPES = ["https://www.googleapis.com/auth/calendar"]

# def get_current_date():
#     return datetime.now().date()

# def extract_meeting_info(user_input):
#     """Extracts meeting information from user input using LLM."""
#     llm_prompt = f"""
#     Extract the following meeting details from the input: '{user_input}'.

#     Required details:
#     - summary: Meeting Summary (if not provided)
#     - location: Any Location (if not provided)
#     - description: Meeting Description (if not provided)
#     - start_date: (format YYYY-MM-DD, interpret relative dates like today, tomorrow, next Monday)
#     - start_time: (format HH:MM)
#     - end_date: (format YYYY-MM-DD)
#     - end_time: (format HH:MM)
#     - time_zone: (default to IST if not provided)
#     - recurrence: (default to "RRULE:FREQ=DAILY;COUNT=1" if not provided)
#     - attendees: (comma-separated emails including the user)
#     - conference_data: (yes/no, default to yes)

#     Consider the current date as {datetime.now().strftime('%Y-%m-%d')}.

#     Return the details in the following format:
#     summary: <summary>
#     location: <location>
#     description: <description>
#     start_date: <start_date>
#     start_time: <start_time>
#     end_date: <end_date>
#     end_time: <end_time>
#     time_zone: <time_zone>
#     recurrence: <recurrence>
#     attendees: <attendees>
#     conference_data: <conference_data>
    
#     If the user does not provide any end_time then set the meeting for 1 hour.
#     """

#     llm = ChatGroq(model="llama-3.1-70b-versatile", temperature=0.2, groq_api_key='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')
#     llm_response = llm.invoke(llm_prompt)

#     llm_output = llm_response.content.strip()
#     llm_data = {}
#     for line in llm_output.split('\n'):
#         if not line.strip():  # Skip empty lines
#             continue
#         try:
#             key, value = line.strip().split(':', 1)
#             llm_data[key.strip().lower()] = value.strip()
#         except ValueError:
#             print(f"Error parsing LLM response line: {line}")  # Log unexpected line

#     return llm_data

# def fetch_attendee_events(service, email):
#     """Fetches events for a given email address."""
#     try:
#         # Get the current date and time
#         now = datetime.now().isoformat() + "Z"

#         # Get the upcoming events
#         event_result = service.events().list(
#             calendarId=email,
#             timeMin=now,
#             maxResults=5,
#             singleEvents=True,
#             orderBy="startTime"
#         ).execute()
#         events = event_result.get("items", [])

#         # Print the details of the upcoming events
#         print(f"\nUpcoming events for {email}:")
#         if not events:
#             print("No upcoming events found!")
#             return

#         for event in events:
#             start = event["start"].get("dateTime", event["start"].get("date"))
#             print(f"{start}: {event.get('summary')}")

#     except HttpError as error:
#         print(f"An error occurred while fetching events for {email}: {error}")

# def get_free_slots(service, attendees, date):
#     """Get available time slots for all attendees on a specific date."""
#     free_slots = []
#     busy_times = []

#     for attendee in attendees:
#         email = attendee["email"]
#         try:
#             # Get the start and end of the day
#             start_of_day = datetime.strptime(f"{date}T00:00:00", "%Y-%m-%dT%H:%M:%S")
#             end_of_day = start_of_day + timedelta(days=1)

#             # Fetch busy times for the attendee
#             body = {
#                 "timeMin": start_of_day.isoformat() + "Z",
#                 "timeMax": end_of_day.isoformat() + "Z",
#                 "timeZone": "Asia/Kolkata",
#                 "items": [{"id": email}]
#             }
#             events = service.freebusy().query(body=body).execute()
#             busy_times.extend(events['calendars'][email]['busy'])
#         except HttpError as error:
#             print(f"An error occurred while fetching busy times for {email}: {error}")

#     # Calculate free slots
#     start_of_day = datetime.strptime(f"{date}T00:00:00", "%Y-%m-%dT%H:%M:%S")
#     end_of_day = start_of_day + timedelta(days=1)

#     if not busy_times:
#         return [(start_of_day.time(), end_of_day.time())]

#     busy_times = sorted(busy_times, key=lambda x: x['start'])
#     free_start = start_of_day

#     for busy in busy_times:
#         busy_start = datetime.fromisoformat(busy["start"].replace('Z', '+00:00'))
#         busy_end = datetime.fromisoformat(busy["end"].replace('Z', '+00:00'))

#         if free_start < busy_start:
#             free_slots.append((free_start.time(), busy_start.time()))

#         free_start = max(free_start, busy_end)

#     if free_start < end_of_day:
#         free_slots.append((free_start.time(), end_of_day.time()))

#     return free_slots

# def main():
#     creds = None

#     if os.path.exists("token.json"):
#         creds = Credentials.from_authorized_user_file("token.json", SCOPES)

#     if not creds or not creds.valid:
#         if creds and creds.expired and creds.refresh_token:
#             creds.refresh(Request())
#         else:
#             flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
#             creds = flow.run_local_server(port=0)

#         with open("token.json", "w") as token:
#             token.write(creds.to_json())

#     try:
#         # Create a service object to interact with the Google Calendar API
#         service = build("calendar", "v3", credentials=creds)

#         user_input = input("Enter your meeting request: ")
#         meeting_details = extract_meeting_info(user_input)

#         # Set default values if keys are missing
#         meeting_details.setdefault('summary', 'Meeting Summary')
#         meeting_details.setdefault('location', 'Any Location')
#         meeting_details.setdefault('description', 'Meeting Description')
#         meeting_details.setdefault('start_date', get_current_date().strftime('%Y-%m-%d'))
#         meeting_details.setdefault('end_date', meeting_details['start_date'])
#         meeting_details.setdefault('time_zone', 'Asia/Kolkata')
#         meeting_details.setdefault('recurrence', 'RRULE:FREQ=DAILY;COUNT=1')
#         meeting_details.setdefault('conference_data', 'yes')

#         # Parse dates and times
#         start_datetime = datetime.strptime(f"{meeting_details['start_date']}T{meeting_details['start_time']}:00", "%Y-%m-%dT%H:%M:%S")
#         end_datetime = datetime.strptime(f"{meeting_details['end_date']}T{meeting_details['end_time']}:00", "%Y-%m-%dT%H:%M:%S")

#         # Parse attendees
#         attendees = [{"email": email.strip()} for email in meeting_details['attendees'].split(",")]

#         # Check for availability of all attendees
#         free_slots = get_free_slots(service, attendees, meeting_details['start_date'])

#         # Determine if the requested time slot is available
#         is_available = False
#         for slot_start, slot_end in free_slots:
#             if slot_start <= start_datetime.time() and slot_end >= end_datetime.time():
#                 is_available = True
#                 break

#         if not is_available:
#             print("Requested time slot is not available.")
#             print("Available slots are:")
#             for slot_start, slot_end in free_slots:
#                 print(f"From {slot_start.strftime('%H:%M')} to {slot_end.strftime('%H:%M')}")
#             return

#         # If available, create the event
#         event = {
#             "summary": meeting_details["summary"],
#             "location": meeting_details["location"],
#             "description": meeting_details["description"],
#             "colorId": 6,
#             "start": {
#                 "dateTime": start_datetime.isoformat(),
#                 "timeZone": meeting_details["time_zone"]
#             },
#             "end": {
#                 "dateTime": end_datetime.isoformat(),
#                 "timeZone": meeting_details["time_zone"]
#             },
#             "recurrence": [
#                 meeting_details["recurrence"]
#             ],
#             "attendees": attendees,
#             "conferenceData": {
#                 "createRequest": {
#                     "requestId": "sample123",
#                     "conferenceSolutionKey": {
#                         "type": "hangoutsMeet"
#                     }
#                 }
#             }
#         }

#         event = service.events().insert(calendarId="primary", body=event, conferenceDataVersion=1).execute()

#         print(f"Event created: {event.get('htmlLink')}")

#     except HttpError as error:
#         print(f"An error occurred: {error}")

# if __name__ == "__main__":
#     main()



import os.path
from datetime import datetime, timedelta
import re
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from langchain_groq import ChatGroq

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

    llm = ChatGroq(model="llama-3.1-70b-versatile", temperature=0.2, groq_api_key='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')
    llm_response = llm.invoke(llm_prompt)

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

def fetch_attendee_events(service, email):
    """Fetches events for a given email address."""
    try:
        # Get the current date and time
        now = datetime.now().isoformat() + "Z"

        # Get the upcoming events
        event_result = service.events().list(
            calendarId=email,
            timeMin=now,
            maxResults=5,
            singleEvents=True,
            orderBy="startTime"
        ).execute()
        events = event_result.get("items", [])

        # Print the details of the upcoming events
        print(f"\nUpcoming events for {email}:")
        if not events:
            print("No upcoming events found!")
            return

        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date"))
            print(f"{start}: {event.get('summary')}")

    except HttpError as error:
        print(f"An error occurred while fetching events for {email}: {error}")

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
        # Create a service object to interact with the Google Calendar API
        service = build("calendar", "v3", credentials=creds)

        user_input = input("Enter your meeting request: ")
        meeting_details = extract_meeting_info(user_input)

        # Set default values if keys are missing
        meeting_details.setdefault('summary', 'Meeting Summary')
        meeting_details.setdefault('location', 'Any Location')
        meeting_details.setdefault('description', 'Meeting Description')
        meeting_details.setdefault('start_date', get_current_date().strftime('%Y-%m-%d'))
        meeting_details.setdefault('end_date', meeting_details['start_date'])
        meeting_details.setdefault('time_zone', 'Asia/Kolkata')
        meeting_details.setdefault('recurrence', 'RRULE:FREQ=DAILY;COUNT=1')
        meeting_details.setdefault('conference_data', 'yes')

        # Parse dates and times
        start_datetime = f"{meeting_details['start_date']}T{meeting_details['start_time']}:00"
        end_datetime = f"{meeting_details['end_date']}T{meeting_details['end_time']}:00"

        # Parse attendees
        attendees = [{"email": email.strip()} for email in meeting_details['attendees'].split(",")]

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
            }
        }

        event = service.events().insert(calendarId="primary", body=event, conferenceDataVersion=1).execute()

        print(f"Event created: {event.get('htmlLink')}")

        # Fetch events for all attendees
        for attendee in attendees:
            email = attendee["email"]
            fetch_attendee_events(service, email)

    except HttpError as error:
        print(f"An error occurred: {error}")

if __name__ == "__main__":
    main()