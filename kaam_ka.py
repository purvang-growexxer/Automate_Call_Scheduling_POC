import os.path
import datetime as dt
from dateutil import parser
import pytz
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/calendar"]

def get_credentials(email):
    creds = None
    token_file = f"token_{email}.json"

    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)

        with open(token_file, "w") as token:
            token.write(creds.to_json())

    return creds

def get_events(service, calendar_id, time_min, time_max):
    event_result = service.events().list(
        calendarId=calendar_id,
        timeMin=time_min,
        timeMax=time_max,
        maxResults=100,
        singleEvents=True,
        orderBy="startTime"
    ).execute()
    events = event_result.get("items", [])
    return events

def find_free_slots(events, day_start, day_end):
    free_slots = []
    last_end_time = day_start

    for event in events:
        start = parser.isoparse(event["start"].get("dateTime", event["start"].get("date")))
        end = parser.isoparse(event["end"].get("dateTime", event["end"].get("date")))

        if end <= day_start or start >= day_end:
            continue

        if start > last_end_time:
            free_slots.append({"start": last_end_time.isoformat(), "end": start.isoformat()})

        last_end_time = max(last_end_time, end)

    if last_end_time < day_end:
        free_slots.append({"start": last_end_time.isoformat(), "end": day_end.isoformat()})

    return free_slots

def print_free_slots(email, free_slots):
    ist = pytz.timezone('Asia/Kolkata')
    print(f"\n{email}'s available time slots:")
    for slot in free_slots:
        start_ist = parser.isoparse(slot['start']).astimezone(ist)
        end_ist = parser.isoparse(slot['end']).astimezone(ist)
        print(f"Start: {start_ist}, End: {end_ist}")

def schedule_call(email, requested_start, requested_end, service):
    event = {
        'summary': 'Scheduled Call',
        'start': {
            'dateTime': requested_start.isoformat(),
            'timeZone': 'Asia/Kolkata',
        },
        'end': {
            'dateTime': requested_end.isoformat(),
            'timeZone': 'Asia/Kolkata',
        },
    }
    event = service.events().insert(calendarId=email, body=event).execute()
    print(f"Call scheduled for {requested_start.astimezone(pytz.timezone('Asia/Kolkata'))}.")

def main():
    try:
        host_email = input("Enter the host's email address: ").strip()
        attendees_emails = input("Enter the attendees' email addresses (comma separated): ").strip().split(",")
        request_date_str = input("Enter the date for the call (YYYY-MM-DD): ").strip()
        request_time_str = input("Enter the time for the call (HH:MM): ").strip()
        request_duration = int(input("Enter the duration of the call in minutes: ").strip())

        request_date = dt.datetime.strptime(request_date_str, '%Y-%m-%d')
        request_time = dt.datetime.strptime(request_time_str, '%H:%M')
        requested_start = dt.datetime.combine(request_date, request_time.time(), tzinfo=pytz.timezone('Asia/Kolkata'))
        requested_end = requested_start + dt.timedelta(minutes=request_duration)

        emails = [host_email] + [email.strip() for email in attendees_emails]

        for email in emails:
            creds = get_credentials(email)
            service = build("calendar", "v3", credentials=creds)
            
            day_start = dt.datetime.combine(request_date, dt.time(hour=0, minute=0), tzinfo=pytz.timezone('Asia/Kolkata'))
            day_end = dt.datetime.combine(request_date, dt.time(hour=23, minute=59), tzinfo=pytz.timezone('Asia/Kolkata'))
            day_start_utc = day_start.astimezone(pytz.UTC).isoformat()
            day_end_utc = day_end.astimezone(pytz.UTC).isoformat()

            events = get_events(service, email, day_start_utc, day_end_utc)

            if not events:
                print(f"No events found for {email} on {request_date_str}!")
                continue

            free_slots = find_free_slots(events, day_start, day_end)
            
            if any(parser.isoparse(slot['start']) <= requested_start < parser.isoparse(slot['end']) and
                   parser.isoparse(slot['start']) < requested_end <= parser.isoparse(slot['end']) for slot in free_slots):
                schedule_call(email, requested_start, requested_end, service)
            else:
                print(f"\nRequested time slot for {email} is not free. Available time slots:")
                print_free_slots(email, free_slots)

    except HttpError as error:
        print("An error occurred:", error)

if __name__ == "__main__":
    main()


# import os.path
# import datetime as dt
# from dateutil import parser
# import pytz
# from google.auth.transport.requests import Request
# from google.oauth2.credentials import Credentials
# from google_auth_oauthlib.flow import InstalledAppFlow
# from googleapiclient.discovery import build
# from googleapiclient.errors import HttpError
 
# SCOPES = ["https://www.googleapis.com/auth/calendar"]
 
# def get_credentials(email):
#     creds = None
#     token_file = f"token_{email}.json"
 
#     if os.path.exists(token_file):
#         creds = Credentials.from_authorized_user_file(token_file, SCOPES)
 
#     if not creds or not creds.valid:
#         if creds and creds.expired and creds.refresh_token:
#             creds.refresh(Request())
#         else:
#             flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
#             creds = flow.run_local_server(port=0)
 
#         with open(token_file, "w") as token:
#             token.write(creds.to_json())
 
#     return creds
 
# def get_events(service, calendar_id):
#     now = dt.datetime.utcnow().isoformat() + "Z"
#     event_result = service.events().list(
#         calendarId=calendar_id,
#         timeMin=now,
#         maxResults=100,  # increase the number of events fetched
#         singleEvents=True,
#         orderBy="startTime"
#     ).execute()
#     events = event_result.get("items", [])
#     return events
 
# def find_free_slots(events):
#     ist = pytz.timezone('Asia/Kolkata')
#     free_slots = []
#     now = dt.datetime.utcnow().replace(tzinfo=pytz.UTC)
#     now_ist = now.astimezone(ist)
 
#     # Define working hours in IST
#     work_start_time = now_ist.replace(hour=11, minute=0, second=0, microsecond=0)
#     work_end_time = now_ist.replace(hour=20, minute=0, second=0, microsecond=0)
 
#     # Adjust for current time within working hours
#     if now_ist > work_start_time and now_ist < work_end_time:
#         work_start_time = now_ist
 
#     last_end_time = work_start_time
 
#     for event in events:
#         start = parser.isoparse(event["start"].get("dateTime", event["start"].get("date"))).astimezone(ist)
#         end = parser.isoparse(event["end"].get("dateTime", event["end"].get("date"))).astimezone(ist)
 
#         # Skip events outside of working hours
#         if end <= work_start_time or start >= work_end_time:
#             continue
 
#         # Adjust start and end times to be within working hours
#         if start < work_start_time:
#             start = work_start_time
#         if end > work_end_time:
#             end = work_end_time
 
#         if start > last_end_time:
#             free_slots.append({"start": last_end_time.isoformat(), "end": start.isoformat()})
 
#         last_end_time = max(last_end_time, end)
 
#     # Check for time after the last event until the end of working hours
#     if last_end_time < work_end_time:
#         free_slots.append({"start": last_end_time.isoformat(), "end": work_end_time.isoformat()})
 
#     return free_slots
 
# def print_free_slots(email, free_slots):
#     ist = pytz.timezone('Asia/Kolkata')
#     print(f"\n{email}'s available time slots:")
#     for slot in free_slots:
#         start_ist = parser.isoparse(slot['start']).astimezone(ist)
#         end_ist = parser.isoparse(slot['end']).astimezone(ist)
#         print(f"Start: {start_ist}, End: {end_ist}")
 
# def main():
#     try:
#         host_email = input("Enter the host's email address: ").strip()
#         attendees_emails = input("Enter the attendees' email addresses (comma separated): ").strip().split(",")
 
#         emails = [host_email] + [email.strip() for email in attendees_emails]
 
#         for email in emails:
#             creds = get_credentials(email)
#             service = build("calendar", "v3", credentials=creds)
#             events = get_events(service, email)
 
#             if not events:
#                 print(f"No upcoming events found for {email}!")
#                 continue
 
#             free_slots = find_free_slots(events)
#             print_free_slots(email, free_slots)
 
#     except HttpError as error:
#         print("An error occurred:", error)
 
# if __name__ == "__main__":
#     main()



# import os.path
# import datetime as dt
# from dateutil import parser
# import pytz
# from google.auth.transport.requests import Request
# from google.oauth2.credentials import Credentials
# from google_auth_oauthlib.flow import InstalledAppFlow
# from googleapiclient.discovery import build
# from googleapiclient.errors import HttpError
 
# SCOPES = ["https://www.googleapis.com/auth/calendar"]
 
# def get_credentials(email):
#     creds = None
#     token_file = f"token_{email}.json"
 
#     if os.path.exists(token_file):
#         creds = Credentials.from_authorized_user_file(token_file, SCOPES)
 
#     if not creds or not creds.valid:
#         if creds and creds.expired and creds.refresh_token:
#             creds.refresh(Request())
#         else:
#             flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
#             creds = flow.run_local_server(port=0)
 
#         with open(token_file, "w") as token:
#             token.write(creds.to_json())
 
#     return creds
 
# def get_events(service, calendar_id):
#     now = dt.datetime.utcnow().isoformat() + "Z"
#     event_result = service.events().list(
#         calendarId=calendar_id,
#         timeMin=now,
#         maxResults=10,
#         singleEvents=True,
#         orderBy="startTime"
#     ).execute()
#     events = event_result.get("items", [])
#     return events
 
# def find_free_slots(events):
#     ist = pytz.timezone('Asia/Kolkata')
#     free_slots = []
#     now = dt.datetime.utcnow().replace(tzinfo=pytz.UTC)
#     now_ist = now.astimezone(ist)
 
#     # Define working hours in IST
#     work_start_time = now_ist.replace(hour=11, minute=0, second=0, microsecond=0)
#     work_end_time = now_ist.replace(hour=20, minute=0, second=0, microsecond=0)
#     # Adjust for current time within working hours
#     if now_ist > work_start_time and now_ist < work_end_time:
#         work_start_time = now_ist
 
#     last_end_time = work_start_time
 
#     for event in events:
#         start = parser.isoparse(event["start"].get("dateTime", event["start"].get("date"))).astimezone(ist)
#         end = parser.isoparse(event["end"].get("dateTime", event["end"].get("date"))).astimezone(ist)
 
#         if start > last_end_time:
#             free_slots.append({"start": last_end_time.isoformat(), "end": start.isoformat()})
 
#         last_end_time = end
 
#     # Check for time after the last event until the end of working hours
#     if last_end_time < work_end_time:
#         free_slots.append({"start": last_end_time.isoformat(), "end": work_end_time.isoformat()})
 
#     return free_slots
 
# def print_free_slots(email, free_slots):
#     ist = pytz.timezone('Asia/Kolkata')
#     print(f"\n{email}'s available time slots:")
#     for slot in free_slots:
#         start_ist = parser.isoparse(slot['start']).astimezone(ist)
#         end_ist = parser.isoparse(slot['end']).astimezone(ist)
#         print(f"Start: {start_ist}, End: {end_ist}")
 
# def main():
#     try:
#         host_email = input("Enter the host's email address: ").strip()
#         attendees_emails = input("Enter the attendees' email addresses (comma separated): ").strip().split(",")
 
#         emails = [host_email] + [email.strip() for email in attendees_emails]
 
#         for email in emails:
#             creds = get_credentials(email)
#             service = build("calendar", "v3", credentials=creds)
#             events = get_events(service, email)
 
#             if not events:
#                 print(f"No upcoming events found for {email}!")
#                 continue
 
#             free_slots = find_free_slots(events)
#             print_free_slots(email, free_slots)
 
#     except HttpError as error:
#         print("An error occurred:", error)
 
# if __name__ == "__main__":
#     main()


    
# import os.path
# import datetime as dt
# from dateutil import parser
# import pytz
# from google.auth.transport.requests import Request
# from google.oauth2.credentials import Credentials
# from google_auth_oauthlib.flow import InstalledAppFlow
# from googleapiclient.discovery import build
# from googleapiclient.errors import HttpError
 
# SCOPES = ["https://www.googleapis.com/auth/calendar"]
 
# def get_credentials(email):
#     creds = None
#     token_file = f"token_{email}.json"
 
#     if os.path.exists(token_file):
#         creds = Credentials.from_authorized_user_file(token_file, SCOPES)
 
#     if not creds or not creds.valid:
#         if creds and creds.expired and creds.refresh_token:
#             creds.refresh(Request())
#         else:
#             flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
#             creds = flow.run_local_server(port=0)
 
#         with open(token_file, "w") as token:
#             token.write(creds.to_json())
 
#     return creds
 
# def get_events(service, calendar_id):
#     now = dt.datetime.utcnow().isoformat() + "Z"
#     event_result = service.events().list(
#         calendarId=calendar_id,
#         timeMin=now,
#         maxResults=10,
#         singleEvents=True,
#         orderBy="startTime"
#     ).execute()
#     events = event_result.get("items", [])
#     return events
 
# def find_free_slots(events):
#     ist = pytz.timezone('Asia/Kolkata')
#     free_slots = []
#     now = dt.datetime.utcnow().replace(tzinfo=pytz.UTC)
#     now_ist = now.astimezone(ist)
 
#     # Define working hours in IST
#     work_start_time = now_ist.replace(hour=11, minute=0, second=0, microsecond=0)
#     work_end_time = now_ist.replace(hour=20, minute=0, second=0, microsecond=0)
#     # Adjust for current time within working hours
#     if now_ist > work_start_time and now_ist < work_end_time:
#         work_start_time = now_ist
 
#     last_end_time = work_start_time
 
#     for event in events:
#         start = parser.isoparse(event["start"].get("dateTime", event["start"].get("date"))).astimezone(ist)
#         end = parser.isoparse(event["end"].get("dateTime", event["end"].get("date"))).astimezone(ist)
 
#         if start > last_end_time:
#             free_slots.append({"start": last_end_time.isoformat(), "end": start.isoformat()})
 
#         last_end_time = end
 
#     # Check for time after the last event until the end of working hours
#     if last_end_time < work_end_time:
#         free_slots.append({"start": last_end_time.isoformat(), "end": work_end_time.isoformat()})
 
#     return free_slots
 
# def print_free_slots(email, free_slots):
#     ist = pytz.timezone('Asia/Kolkata')
#     print(f"\n{email}'s available time slots:")
#     for slot in free_slots:
#         start_ist = parser.isoparse(slot['start']).astimezone(ist)
#         end_ist = parser.isoparse(slot['end']).astimezone(ist)
#         print(f"Start: {start_ist}, End: {end_ist}")
 
# def main():
#     try:
#         host_email = input("Enter the host's email address: ").strip()
#         attendees_emails = input("Enter the attendees' email addresses (comma separated): ").strip().split(",")
 
#         emails = [host_email] + [email.strip() for email in attendees_emails]
 
#         for email in emails:
#             creds = get_credentials(email)
#             service = build("calendar", "v3", credentials=creds)
#             events = get_events(service, email)
 
#             if not events:
#                 print(f"No upcoming events found for {email}!")
#                 continue
 
#             free_slots = find_free_slots(events)
#             print_free_slots(email, free_slots)
 
#     except HttpError as error:
#         print("An error occurred:", error)
 
# if __name__ == "__main__":
#     main()