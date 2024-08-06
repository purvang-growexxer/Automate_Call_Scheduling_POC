import os.path
import datetime as dt
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
 
SCOPES = ["https://www.googleapis.com/auth/calendar"]
 
def main():
    creds = None
 
    # Check if the token.json file exists
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
 
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())
 
    try:
        # Create a service object to interact with the Google Calendar API
        service = build("calendar", "v3", credentials=creds)
 
        # Prompt user to input the colleague's calendar ID (email address)
        colleague_calendar_id = input("Enter the colleague's email address for calendar access: ").strip()
 
        # Get the current date and time
        now = dt.datetime.utcnow().isoformat() + "Z"
 
        # Get the upcoming events
        event_result = service.events().list(
            calendarId=colleague_calendar_id,
            timeMin=now,
            maxResults=10,
            singleEvents=True,
            orderBy="startTime"
        ).execute()
        events = event_result.get("items", [])
 
        # If no events are found, print a message
        if not events:
            print("No upcoming events found!")
            return
        
        # Print the details of the upcoming events
        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date"))
            end = event["end"].get("dateTime", event["end"].get("date"))
            summary = event.get("summary", "No Title")
            print(f"Event: {summary}\nStart: {start}\nEnd: {end}\n")
 
        # Find free slots between events
        free_slots = []
        last_end_time = now
 
        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date"))
            if start > last_end_time:
                free_slots.append({"start": last_end_time, "end": start})
            last_end_time = event["end"].get("dateTime", event["end"].get("date"))
 
        # If the last event ends before the end of the day, add the remaining time as a free slot
        end_of_day = (dt.datetime.utcnow().replace(hour=23, minute=59, second=59)).isoformat() + "Z"
        if last_end_time < end_of_day:
            free_slots.append({"start": last_end_time, "end": end_of_day})
 
        # Print the free slots
        print("Free slots:")
        for slot in free_slots:
            print(f"Start: {slot['start']}, End: {slot['end']}")
 
    except HttpError as error:
        print("An error occurred:", error)
 
if __name__ == "__main__":
    main()
