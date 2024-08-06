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
        creds = Credentials.from_authorized_user_file("token.json")
 
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
 
        # Get the current date and time
        now = dt.datetime.now().isoformat() + "Z"
 
        # Get the upcoming events
        event_result = service.events().list(
            calendarId="primary",
            timeMin=now,
            maxResults=5,
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
            print(start, event.get("summary"))
 
        # Uncomment and modify the following code to create a new event
        # event = {
        #     "summary": "My Python Event",
        #     "location": "Somewhere Online",
        #     "description": "Some more details on this awesome event",
        #     "colorId": 6,
        #     "start": {
        #         "dateTime": "2024-08-06T11:30:00",
        #         "timeZone": "Asia/Kolkata"
        #     },
        #     "end": {
        #         "dateTime": "2024-08-06T12:00:00",
        #         "timeZone": "Asia/Kolkata"
        #     },
        #     "recurrence": [
        #         "RRULE:FREQ=DAILY;COUNT=3"
        #     ],
        #     "attendees": [
        #         {"email": "maheriapv2003@gmail.com"}
        #     ]
        # }
        # event = service.events().insert(calendarId="primary", body=event).execute()
        # print("Event created:", event.get("htmlLink"))
 
    except HttpError as error:
        print("An error occurred:", error)
 
if __name__ == "__main__":
    main()
