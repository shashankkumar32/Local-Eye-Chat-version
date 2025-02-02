import os
import json
import threading
import flet as ft
import ollama
from datetime import datetime
from flet import colors

# Storage file for chat history
HISTORY_FILE = "chat_history.json"
current_loaded_date = None


def save_chat_history(chat_display, date):
    """Save chat history to a JSON file, appending to existing history for the date."""
    history = []
    for msg in chat_display.controls:
        print(f"Processing message: {msg}")  # Debug print
        if isinstance(msg, ft.Text):
            if msg.value.startswith("You: "):
                user_content = msg.value[len("You: "):]
                history.append({"role": "user", "content": user_content})
                print(f"Appending User Text:{user_content}")  # Debug print
            elif msg.value.startswith("Assistant: "):
                assistant_content = msg.value[len("Assistant: "):]
                history.append({"role": "assistant", "content": assistant_content})
                print(f"Appending Assistant Text:{assistant_content}")  # Debug print
        elif isinstance(msg, ft.Card) and isinstance(msg.content, ft.Container) and isinstance(msg.content.content, ft.Column):
             for text in msg.content.content.controls:
                if isinstance(text, ft.Text):
                    if text.value.startswith("You: "):
                        user_content = text.value[len("You: "):]
                        history.append({"role": "user", "content": user_content})
                        print(f"Appending User Text in Card:{user_content}")  # Debug print
                    elif text.value.startswith("Assistant: "):
                        assistant_content = text.value[len("Assistant: "):]
                        history.append({"role": "assistant", "content": assistant_content})
                        print(f"Appending Assistant Text in Card:{assistant_content}")  # Debug print
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            try:
                all_history = json.load(f)
            except json.JSONDecodeError:
                all_history = {}  # Handle empty or corrupted file

    else:
        all_history = {}

    if date in all_history:
        all_history[date].extend(history)
    else:
        all_history[date] = history
    print(f"Saving History: {all_history}")  # Debug Print
    try:
        with open(HISTORY_FILE, "w") as f:
            json.dump(all_history, f, indent=4)
    except Exception as e:
        print(f"Error writing JSON file: {e}")
    print(f"Saved chat history for date {date}")  # Debug Print

def load_chat_history(date, chat_display, page):
    """Load chat history for a specific date from the JSON file."""
    global current_loaded_date
    if current_loaded_date != date:
        chat_display.controls.clear()
        current_loaded_date = date
    else:
        return  # Prevent duplicate loading

    if os.path.exists(HISTORY_FILE) and os.stat(HISTORY_FILE).st_size > 0:
        try:
            with open(HISTORY_FILE, "r") as f:
                all_history = json.load(f)

            if date in all_history:
                paired_messages = []
                current_pair = []
                for msg in all_history[date]:
                    current_pair.append(msg)
                    if len(current_pair) == 2:
                        paired_messages.append(current_pair)
                        current_pair = []
                if current_pair:
                    paired_messages.append(current_pair)

                for pair in paired_messages:
                    if len(pair) == 2:
                        user_msg = pair[0]["content"]
                        assistant_msg = pair[1]["content"]
                        chat_display.controls.append(
                            ft.Card(
                                content=ft.Container(
                                    content=ft.Column([
                                        ft.Text(f"You: {user_msg}", weight=ft.FontWeight.BOLD, color=colors.WHITE),
                                        ft.Text(f"Assistant: {assistant_msg}", selectable=True, color=colors.WHITE)
                                    ]),
                                    padding=10,
                                    bgcolor=colors.BLACK,
                                    border_radius=10,
                                ),
                                elevation=2,

                            )
                        )
                    elif len(pair) == 1:
                        msg = pair[0]
                        prefix = "You: " if msg["role"] == "user" else "Assistant: "
                        chat_display.controls.append(
                            ft.Card(
                                content=ft.Container(
                                    content=ft.Text(f"{prefix}{msg['content']}", color=colors.WHITE),
                                    padding=10,
                                    bgcolor=colors.BLACK,
                                    border_radius=10
                                ),
                                elevation=2,

                            )
                        )
            chat_display.update()
            page.update()
            if chat_display.controls:
                chat_display.scroll_to(
                    offset=chat_display.get_scroll_extent(),
                    animate=ft.animation.Animation(duration=600,
                                                    curve=ft.AnimationCurve.EASE_IN_OUT)
                    )

        except json.JSONDecodeError:
            print("Error: Failed to decode chat history.")
        except Exception as e:
            print(f"Unexpected error: {e}")


def load_available_dates():
    """Retrieve available chat dates from the history file."""
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            try:
                all_history = json.load(f)
                return sorted(all_history.keys(), reverse=True)
            except json.JSONDecodeError:
                return []
    return []


def main(page: ft.Page):
    page.title = "Local-Eye"
    page.window_icon = "C:/Users/shash/flet-project/flet-icon.png"  # Full path
    page.window.title_bar_hidden = True
    page.window.title_bar_buttons_hidden = True
    page.window.bgcolor = ft.Colors.TRANSPARENT
    page.window.left = 400
    page.window.top = 200
    page.window_width = 800
    page.window_height = 700
    page.theme_mode = "dark"
    page.window_undecorated = True
   


    chat_area_placeholder = ft.Text("Start a new chat to see the history here", style=ft.TextStyle(size=18),
                                    color=colors.GREY)
    current_date = datetime.now().strftime("%Y-%m-%d")
    global current_loaded_date
    current_loaded_date = current_date

    models_response = ollama.list()
    model_list = [model.model for model in models_response.models] if models_response.models else ["llama3"]

    selected_model = ft.Dropdown(
        options=[ft.dropdown.Option(model) for model in model_list],
        value=model_list[0],
        label="Select Model",
        width=200,
        border_radius=25,
        label_style=ft.TextStyle(color=colors.BLACK, weight=ft.FontWeight.BOLD),
        text_style=ft.TextStyle(color=colors.BLACK),
        border_color=colors.BLACK,
        focused_border_color=colors.BLACK,
        
        
        
    )
    
    chat_display = ft.ListView(expand=True, spacing=10, padding=10, height=550)
    date_sidebar = ft.ListView(width=150, padding=10)
    date_sidebar_heading = ft.Text("History", style=ft.TextStyle(weight=ft.FontWeight.BOLD), color=colors.WHITE,
                                   size=17)

    def refresh_dates():
        """Refresh the list of available chat dates in the sidebar."""
        date_sidebar.controls.clear()
        dates = load_available_dates()
        if dates:
            for date in dates:
                date_sidebar.controls.append(
                    ft.Card(
                        content=ft.Container(
                            content=ft.TextButton(
                                text=date,
                                on_click=lambda e, d=date: load_chat_history(d, chat_display, page),
                                style=ft.ButtonStyle(
                                    padding=ft.padding.only(left=10, right=10),
                                    shape=ft.CircleBorder(),
                                )
                            ),
                            bgcolor=colors.BLACK,
                            border_radius=10,
                            padding=10
                        ),
                        elevation=2,

                    )
                )

            if chat_area_placeholder in chat_display.controls:
                chat_display.controls.remove(chat_area_placeholder)
        else:
            date_sidebar.controls.append(ft.Text("No History Yet", style=ft.TextStyle(size=15), color=colors.GREY))
        page.update()

    user_input = ft.TextField(
        hint_text="Type your message...  use SHIFT + ENTER to send chat",
        border_radius=15,
        expand=True,
        color=colors.BLACK,
        text_style=ft.TextStyle(color=colors.BLACK)
    )

    send_button = ft.Container(
        content=ft.IconButton(icon=ft.Icons.SEND, on_click=lambda e: send_message()),
        margin=ft.margin.only(bottom=10)
    )

    def send_message():
        message = user_input.value.strip()
        if not message:
            return

        if chat_area_placeholder in chat_display.controls:
            chat_display.controls.remove(chat_area_placeholder)

        user_message = ft.Text(f"You: {message}", weight=ft.FontWeight.BOLD, color=colors.WHITE)
        chat_display.controls.append(user_message)
        print(f"Added user message to chat display: {message}") # Debug Print
        user_input.value = ""
        page.update()
       
        def fetch_response():
             response_text = ft.Text("Assistant: ", selectable=True, color=colors.WHITE)
             chat_display.controls.append(response_text)
             print(f"Added assistant response to chat display.") # Debug Print
             page.update()

             response = ollama.generate(model=selected_model.value, prompt=message)
             bot_reply = response["response"]
             response_text.value = f"Assistant: {bot_reply}"
             print(f"Set the assistant response to: {bot_reply}") # Debug Print
             page.update()
             save_chat_history(chat_display, current_date)
             refresh_dates()

        threading.Thread(target=fetch_response, daemon=True).start()
    
    def handle_key_event(e: ft.KeyboardEvent):
        if e.key == "Enter" and e.shift:
            send_message()


    load_chat_history(current_date, chat_display, page)
    page.on_keyboard_event = handle_key_event


    def close_window(e):
        page.window_close()
        
    close_button = ft.IconButton(
        icon=ft.icons.CLOSE,

         on_click=lambda _: page.window.close(),
        tooltip="Close Window",
        style=ft.ButtonStyle(
            padding=0,
            shape=ft.CircleBorder(),
        ),
    )
    
    app_bar = ft.WindowDragArea(ft.Container(
        content=ft.Row(
            [
                ft.Text("   Local-Eye", weight=ft.FontWeight.BOLD, color=colors.BLACK),
                ft.Row(
                  [
                  selected_model,
                  close_button,
                  ],
                  alignment=ft.MainAxisAlignment.END,
                   spacing=0
                  )
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        ),
        padding=ft.padding.only(left=10, right=10, top=10, bottom=10),
        height=70, border_radius=ft.border_radius.only(top_left=15, top_right=15), bgcolor=colors.WHITE
    ))

    date_header = ft.Container(content=ft.Column([date_sidebar_heading, date_sidebar]), width=180,
                               bgcolor=colors.BLACK,
                               border_radius=ft.border_radius.only(bottom_left=15, bottom_right=15), padding=10)
    date_sidebar_container = ft.Container(content=ft.Column([date_header]), width=180, bgcolor=colors.BLACK)

    input_area = ft.Container(content=ft.Row([user_input, send_button]), height=50, padding=10, border_radius=15,
                              margin=ft.margin.only(10), bgcolor=colors.WHITE)

    chat_area = ft.Column([chat_display, input_area], expand=True)

    if not chat_display.controls:
        chat_display.controls.append(chat_area_placeholder)

    page.add(app_bar, ft.Row([chat_area, date_sidebar_container], expand=True))

    refresh_dates()
    page.on_close = lambda _: save_chat_history(chat_display, current_date)


ft.app(target=main)
