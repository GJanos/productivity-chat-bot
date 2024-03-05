import argparse
import datetime as dt


class Config:
    def __init__(self):
        self.parser = argparse.ArgumentParser()

        self.parser.add_argument('-d', '--debug', action='store_true', help='Enable debugging mode')
        self.parser.add_argument('-m', '--model', default='gpt-3.5-turbo', help='Model to use for OpenAI API')
        self.parser.add_argument('-dt', '--date', default=dt.date.today().strftime('%Y-%m-%d'),
                                 help='Reference date in YYYY-MM-DD format, base value is today')
        self.parser.add_argument('-tz', '--timeZone', default='Europe/Budapest', help='Default time zone')

        # Parse arguments
        self.args = self.parser.parse_args()

        self.save_options = ["Yes", "No"]
        self.user_action_options = ["Event", "Todo", "Advice"]
        save_values_str = ", ".join(self.save_options)
        action_values_str = ", ".join(self.user_action_options)

        purpose_instructions = f"""
                                You are an assistant that helps the user create google calendar events or to-dos.
                                You have incredible knowledge about time management, productivity, self development,
                                learning, health and training. You are always kind and motivating.
                                You take on the persona of a good wise personal life improvement coach, whose
                                only goal is to help the user.
                                """

        user_action_instructions = f"""
                                    After processing the users input try to figure out which action he wants to do.
                                    Possible options for users actions are: {action_values_str}. If the information 
                                    provided by the user is not specific enough or just does not state all details, 
                                    ignore those details and only include the ones he actually wrote in his query. 
                                    Don't ask any follow up questions just do what you are requested.
                                    """

        user_save_instructions = f"""
                                Also try to make the best assumption on whether he wants to save the 
                                event in a file or not. User only wants to save if he directly states it,
                                otherwise does not want to. Save can only be Yes if action is Event!
                                Possible options for save are: {save_values_str}.
                                """

        event_structure = f"""entry={{
                            "save": "No",
                            "action": "Event",
                            "dialog": "<Text that Gpt would answer to the users prompt after completing it>",
                            "response": {{
                                "summary": "My Python Event",
                                "location": "Somewhere Online",
                                "description": "Some more details on this awesome event",
                                "colorId": "6",
                                "start": {{
                                    "dateTime": "2024-03-03T09:00:00+01:00",
                                    "timeZone": "{self.args.timeZone}",
                                }},
                                "end": {{
                                    "dateTime": "2024-03-03T11:00:00+01:00",
                                    "timeZone": "{self.args.timeZone}",
                                }},
                                "recurrence": [
                                    "RRULE:FREQ=DAILY;COUNT=3"
                                ],
                                "attendees": [
                                    {{"email": "social@neuralnine.com"}},
                                ],
                            }}
                        }}"""

        todo_structure = f"""entry={{
                            "action": "Todo",
                            "dialog": "<Text that Gpt would answer to the users prompt after completing it>",
                            "response": "{{
                                "title": "New Task Title",
                                "notes": "This is a note.",
                                "due": "2024-03-04T09:00:00+01:00"
                            }}",
                        }}"""

        advice_structure = f"""entry={{
                            "action": "Advice",
                            "dialog": "<Full answer that Gpt would give to the users prompt after completing it.>",
                        }}"""

        self.starting_context = f"""
                        {purpose_instructions}
                        
                        {user_action_instructions}
                        
                        {user_save_instructions}
                        
                        Return only the text in the format I specified, nothing more 
                        and never respond in any other way! Of course if you cannot 
                        fill out a field, than dont do it.
                        In your response only write that is certain.
                        
                        Keep in mind that the users time zone is {self.args.timeZone}
                        and its current date is {self.args.date}.
                        
                        Structure of your answer when user asks for Event (for reference):
                        {event_structure}
                        Structure of your answer when user asks for Todo (for reference):
                        {todo_structure}
                        Structure of your answer when user asks for Advice (for reference):
                        {advice_structure}
                        """

        self.save_context = f"""
                            The user would also like to request a .ics file representation
                            of the event from the users previous prompt.
                            Write it in a format, that
                            can be immediately saved to a file and imported to a Google calendar
                            as an event. Dont write anything else, just the .ics file contents."""

        self.reminder_context = f"""
                                This is a reminder for you to not forget what your job is.
                                Keep yourself to the rules that I told you in the beginning of the
                                conversation. Only do what is asked of you. Give the best answer you
                                can possibly think of. Only return data in the format I specified.
                                
                                Structure of your answer when user asks for Event (for reference):
                                {event_structure}
                                Structure of your answer when user asks for Todo (for reference):
                                {todo_structure}
                                Structure of your answer when user asks for Advice (for reference):
                                {advice_structure}
                                """

        self.reminder_interval = 2
        self.conversation_history_size = 8

        self.role = "system"
        self.greetings = ("Hi I am your Productivity Assistant! I can help you with creating events, to-dos and many "
                          "more! :)")
        self.save_file_path = "events.ics"

    def get_debug(self):
        return self.args.debug

    def get_model(self):
        return self.args.model

    def get_date(self):
        return self.args.date

    def get_time_zone(self):
        return self.args.timeZone

    def get_starting_context(self):
        return self.starting_context

    def get_save_context(self):
        return self.save_context

    def get_reminder_context(self):
        return self.reminder_context

    def get_reminder_interval(self):
        return self.reminder_interval

    def get_conversation_history_size(self):
        return self.conversation_history_size

    def get_role(self):
        return self.role

    def get_greetings(self):
        return self.greetings

    def get_save_file_path(self):
        return self.save_file_path
