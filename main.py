# google imports
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# openai imports
from dotenv import load_dotenv
from openai import OpenAI

# project imports
from Config import Config
import json
import os.path
import sys

# If modifying these SCOPES, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar',
          'https://www.googleapis.com/auth/tasks']

GOOGLE_CALENDAR_SERVICE_NAME = 'calendar'
GOOGLE_CALENDAR_API_VERSION = 'v3'
GOOGLE_CALENDAR_CLIENT_ID = 'primary'

GOOGLE_TASKS_SERVICE_NAME = 'tasks'
GOOGLE_TASKS_API_VERSION = 'v1'
GOOGLE_TASKS_TASKLIST_ID = '@default'


def setup_google_credentials():
    """Set up Google API credentials, refreshing or creating them if necessary."""
    try:
        creds = None
        token_path = os.path.join('auth', 'token.json')
        credentials_path = os.path.join('auth', 'credentials.json')

        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)
            with open(token_path, 'w') as token:
                token.write(creds.to_json())

        return creds

    except Exception as error:
        print(f"Error setting up Google API credentials: {error}")
        sys.exit(1)


def setup_calendar_client():
    """Set up Google client for Calendar."""
    return build(GOOGLE_CALENDAR_SERVICE_NAME,
                 GOOGLE_CALENDAR_API_VERSION,
                 credentials=google_creds)


def setup_tasks_client():
    """Set up Google client for Tasks."""
    return build(GOOGLE_TASKS_SERVICE_NAME,
                 GOOGLE_TASKS_API_VERSION,
                 credentials=google_creds)


def setup_gpt_client():
    """Set up the GPT client with the API key from environment variables."""
    try:
        load_dotenv()
        api_key = os.environ.get("OPENAI_API_KEY")
        if api_key is None:
            raise ValueError("The OPENAI_API_KEY environment variable must be set.")

        return OpenAI(api_key=api_key)

    except Exception as error:
        print(f"Error setting up GPT client: {error}")
        sys.exit(1)


# setting up project scope global states
config = Config()
google_creds = setup_google_credentials()
calendar_client = setup_calendar_client()
tasks_client = setup_tasks_client()
gpt_client = setup_gpt_client()
reminder_counter = 0


def print_debug_text(message):
    """Print the message if debugging is enabled."""
    if config.get_debug():
        print(message)


def print_debug_message_memory(message_memory):
    if config.get_debug():
        print("Message Memory:")
        for i, message in enumerate(message_memory, start=1):
            role = message.get('role', 'Unknown role')
            content = message.get('content', 'No content')
            print(f"Message {i}:")
            print(f"  Role: {role}")
            print(f"  Content: {content}\n")


def add_prompt_to_message_memory(message_memory, message):
    """Add a message to the message memory, if size is smaller than the
    maximum size, otherwise it acts as a queue and pop out old messages
    except the initial starting_context form position 0."""

    max_size = config.get_conversation_history_size()
    if len(message_memory) >= max_size:
        del message_memory[1]

    message_memory.append(message)


def get_user_prompt(message_memory):
    """Get user prompt and save it to message_memory."""
    user_prompt = input()
    add_prompt_to_message_memory(message_memory,
                                 {"role": "system",
                                  "content": user_prompt})
    return user_prompt


def remind_gpt_if_needed(message_memory):
    """Reminds GPT every config.reminder_interval request of the purpose of the bot."""
    global reminder_counter
    reminder_counter += 1

    if config.reminder_interval == reminder_counter:
        add_prompt_to_message_memory(message_memory,
                                     {"role": "system",
                                      "content": config.reminder_context})
        reminder_counter = 0


def send_gpt_request(message_memory):
    """Send users prompt to Gpt and accepts response."""
    try:
        remind_gpt_if_needed(message_memory)

        completion = gpt_client.chat.completions.create(
            model=config.get_model(),
            messages=message_memory
        )

        gpt_response = completion.choices[0].message.content.strip()
        add_prompt_to_message_memory(message_memory,
                                     {"role": "system",
                                      "content": gpt_response})
        return gpt_response

    except Exception as error:
        print(f"An error occurred while sending request to GPT: {error}\nTry again with other prompt.")


def save_google_calendar_event_to_file(message_memory):
    """Save Google Calendar event into file that can be imported."""
    try:
        # smaller memory containing only the base context (ind. 0)
        # previous message (ind. -1) and save_contex
        save_memory = [message_memory[0], message_memory[-1], {"role": "system", "content": config.get_save_context()}]
        gpt_response = send_gpt_request(save_memory)

        with open(config.save_file_path, "w") as file:
            file.write(gpt_response)

        print_debug_text(f"File {config.save_file_path} saved.")

    except Exception as error:
        print(f"An error occurred while saving calendat event: {error}\nTry again with other prompt.")


def valid_user_action(user_action):
    """Validate user action determined by Gpt"""
    return user_action in config.user_action_options


def create_google_calendar_event(gpt_response):
    event_data = gpt_response["response"]
    calendar_client.events().insert(calendarId=GOOGLE_CALENDAR_CLIENT_ID,
                                    body=event_data).execute()

    print_debug_text(f"Event data: {event_data}")


def create_google_tasks_task(gpt_response):
    task_data = gpt_response["response"]
    tasks_client.tasks().insert(tasklist=GOOGLE_TASKS_TASKLIST_ID,
                                body=task_data).execute()

    print_debug_text(f"Task data: {task_data}")


def handle_gpt_response(gpt_response, message_memory):
    """Create a new Google calendar event based on Gpt's response"""
    try:
        gpt_response = json.loads(gpt_response)
        print_debug_text(f"Gpt response json: {gpt_response}")

        user_action = gpt_response["action"]
        if valid_user_action(user_action):

            dialog = gpt_response["dialog"]
            if user_action == "Event":
                create_google_calendar_event(gpt_response)

                if gpt_response["save"] == "Yes":
                    save_google_calendar_event_to_file(message_memory)

            elif user_action == "Todo":
                create_google_tasks_task(gpt_response)

            # dialog part of response always gets printed
            # if user_action is Advice, then we only have a conversation
            # which only needs a dialog
            print(f"{dialog}")
        else:
            print(f"Invalid user action detected: {user_action}")

    except json.JSONDecodeError as error:
        print(f"Error decoding GPT response as JSON: {error}\nTry again with other prompt.")
    except HttpError as error:
        print(f"An error occurred with the Google Calendar API: {error}\nTry again with other prompt.")


def main():
    message_memory = [{"role": config.get_role(), "content": config.get_starting_context()}, ]

    print(f"{config.get_greetings()}")
    user_prompt = get_user_prompt(message_memory)

    while user_prompt not in ["quit", "exit", "over", "done", "bye"]:
        gpt_response = send_gpt_request(message_memory)
        print_debug_text(f"Gpt response json: {gpt_response}")

        handle_gpt_response(gpt_response, message_memory)
        print_debug_message_memory(message_memory)

        user_prompt = get_user_prompt(message_memory)


if __name__ == '__main__':
    main()
