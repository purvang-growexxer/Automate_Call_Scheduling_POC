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
 
def get_events(service, calendar_id, date):
    start_of_day = dt.datetime.combine(date, dt.time.min).astimezone(pytz.utc).isoformat()
    end_of_day = dt.datetime.combine(date, dt.time.max).astimezone(pytz.utc).isoformat()
    event_result = service.events().list(
        calendarId=calendar_id,
        timeMin=start_of_day,
        timeMax=end_of_day,
        singleEvents=True,
        orderBy="startTime"
    ).execute()
    events = event_result.get("items", [])
    return events
 
def find_free_slots(events, date):
    ist = pytz.timezone('Asia/Kolkata')
    free_slots = []
 
    # Define working hours in IST
    work_start_time = ist.localize(dt.datetime.combine(date, dt.time(11, 0, 0)))
    work_end_time = ist.localize(dt.datetime.combine(date, dt.time(20, 0, 0)))
 
    last_end_time = work_start_time
 
    for event in events:
        start = parser.isoparse(event["start"].get("dateTime", event["start"].get("date"))).astimezone(ist)
        end = parser.isoparse(event["end"].get("dateTime", event["end"].get("date"))).astimezone(ist)
 
        # Skip events outside of working hours
        if end <= work_start_time or start >= work_end_time:
            continue
 
        # Adjust start and end times to be within working hours
        if start < work_start_time:
            start = work_start_time
        if end > work_end_time:
            end = work_end_time
 
        if start > last_end_time:
            free_slots.append({"start": last_end_time.isoformat(), "end": start.isoformat()})
 
        last_end_time = max(last_end_time, end)
 
    # Check for time after the last event until the end of working hours
    if last_end_time < work_end_time:
        free_slots.append({"start": last_end_time.isoformat(), "end": work_end_time.isoformat()})
 
    return free_slots
 
def print_free_slots(email, free_slots):
    ist = pytz.timezone('Asia/Kolkata')
    print(f"\n{email}'s available time slots:")
    for slot in free_slots:
        start_ist = parser.isoparse(slot['start']).astimezone(ist)
        end_ist = parser.isoparse(slot['end']).astimezone(ist)
        print(f"Start: {start_ist}, End: {end_ist}")
 
def find_common_free_slots(all_free_slots, date):
    ist = pytz.timezone('Asia/Kolkata')
    work_start_time = ist.localize(dt.datetime.combine(date, dt.time(11, 0, 0)))
    work_end_time = ist.localize(dt.datetime.combine(date, dt.time(20, 0, 0)))
 
    # Initialize with the entire working hours as the initial common free slot
    common_free_slots = [{"start": work_start_time, "end": work_end_time}]
 
    for free_slots in all_free_slots:
        new_common_slots = []
        for common_slot in common_free_slots:
            for slot in free_slots:
                slot_start = parser.isoparse(slot['start']).astimezone(ist)
                slot_end = parser.isoparse(slot['end']).astimezone(ist)
                latest_start = max(common_slot['start'], slot_start)
                earliest_end = min(common_slot['end'], slot_end)
 
                if latest_start < earliest_end:
                    new_common_slots.append({"start": latest_start, "end": earliest_end})
        common_free_slots = new_common_slots
 
    return common_free_slots
 
def print_common_free_slots(common_free_slots):
    ist = pytz.timezone('Asia/Kolkata')
    print("\nCommon available time slots:")
    for slot in common_free_slots:
        start_ist = slot['start'].astimezone(ist)
        end_ist = slot['end'].astimezone(ist)
        print(f"Start: {start_ist}, End: {end_ist}")
 
def main():
    try:
        host_email = input("Enter the host's email address: ").strip()
        attendees_emails = input("Enter the attendees' email addresses (comma separated): ").strip().split(",")
        date_str = input("Enter the date (YYYY-MM-DD) to check availability: ").strip()
        date = dt.datetime.strptime(date_str, "%Y-%m-%d").date()
 
        emails = [host_email] + [email.strip() for email in attendees_emails]
 
        all_free_slots = []
 
        for email in emails:
            creds = get_credentials(email)
            service = build("calendar", "v3", credentials=creds)
            events = get_events(service, email, date)
 
            if not events:
                print(f"No upcoming events found for {email} on {date_str}!")
                continue
 
            free_slots = find_free_slots(events, date)
            all_free_slots.append(free_slots)
            print_free_slots(email, free_slots)
 
        if all_free_slots:
            common_free_slots = find_common_free_slots(all_free_slots, date)
            print_common_free_slots(common_free_slots)
 
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
 
# def get_events(service, calendar_id, date):
#     start_of_day = dt.datetime.combine(date, dt.time.min).astimezone(pytz.utc).isoformat()
#     end_of_day = dt.datetime.combine(date, dt.time.max).astimezone(pytz.utc).isoformat()
#     event_result = service.events().list(
#         calendarId=calendar_id,
#         timeMin=start_of_day,
#         timeMax=end_of_day,
#         singleEvents=True,
#         orderBy="startTime"
#     ).execute()
#     events = event_result.get("items", [])
#     return events
 
# def find_free_slots(events, date):
#     ist = pytz.timezone('Asia/Kolkata')
#     free_slots = []
 
#     # Define working hours in IST
#     work_start_time = ist.localize(dt.datetime.combine(date, dt.time(11, 0, 0)))
#     work_end_time = ist.localize(dt.datetime.combine(date, dt.time(20, 0, 0)))
 
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
#         date_str = input("Enter the date (YYYY-MM-DD) to check availability: ").strip()
#         date = dt.datetime.strptime(date_str, "%Y-%m-%d").date()
 
#         emails = [host_email] + [email.strip() for email in attendees_emails]
 
#         for email in emails:
#             creds = get_credentials(email)
#             service = build("calendar", "v3", credentials=creds)
#             events = get_events(service, email, date)
 
#             if not events:
#                 print(f"No upcoming events found for {email} on {date_str}!")
#                 continue
 
#             free_slots = find_free_slots(events, date)
#             print_free_slots(email, free_slots)
 
#     except HttpError as error:
#         print("An error occurred:", error)
 
# if __name__ == "__main__":
#     main()