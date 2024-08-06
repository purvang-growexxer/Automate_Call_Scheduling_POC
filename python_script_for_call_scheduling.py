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

    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json")

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())

        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)

        with open("token.json", "w") as token:
            token.write(creds.to_json())
    
    try:
        service = build("calendar", "v3", Credentials=creds)

        # # commented code for listing the events only
        # now = dt.datetime.now().isoformat() + "Z"

        # event_result = service.events().list(calendarId = "primary", timeMin=now, maxResults=5, singleEvents = True, orderBy="startTime").execute()
        # events = event_result.get("items", [])

        # if not events:
        #     print("No upcoming events found!")
        #     return 
        
        # for event in events:
        #     start = event["start"].get("dateTime", event["start"].get("date"))
        #     print(start, event["Summary"])

        # # <----------------------------------------------------------------------->

        event = {

            "summary": "My Python Event",
            "Location": "Somewhere Online",
            "description": "Some more details on this awesome event",
            "colorId": 6,
            "start": {
                "dateTime": "2024-08-06T11:30:00",
                "timeZone": "Asia/Kolkata"
            },
            "end": {
                "dateTime": "2024-08-06T12:00:00",
                "timeZone": "Asia/Kolkata"
            },
            "recurrence":[
                "RRULE:FREQ=DAILY;COUNT=3"
            ],
            "attendees": [
                {"email": "maheriapv2003@gmail.com"}
            ]
        }


        event = service.events().insert(calendarId = "primary", body = event).execute()

        print("Event created {event.get(htmlLink)}")



    except HttpError as error:
        print("An error occured:", error)

if __name__ == "__main__":
    main()

    