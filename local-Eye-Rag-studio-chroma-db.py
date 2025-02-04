import flet as ft
import chromadb
import ollama
import fitz  # PyMuPDF for PDF processing
from datetime import datetime
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

# Initialize ChromaDB with SentenceTransformer
embedding_function = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection(name="chat_history", embedding_function=embedding_function)

# Debug: Print the first 5 stored chats
print("🔹 Initial ChromaDB State:", collection.peek(5))

def save_chat(user, message):
    """Saves a chat message to ChromaDB."""
    timestamp = datetime.now().isoformat()
    print(f"📝 Saving Chat - {user}: {message}")  # Debugging
    collection.add(
        documents=[message],
        metadatas=[{"user": user, "timestamp": timestamp}],
        ids=[timestamp]
    )

def retrieve_chats_by_date(date):
    """Retrieve chats for a specific date."""
    results = collection.get()
    chats = [
        f"{meta['timestamp']} - {meta['user']}: {doc}"
        for meta, doc in zip(results["metadatas"], results["documents"])
        if date in meta["timestamp"]
    ]
    return chats

def retrieve_relevant_chats(query, n=5):
    """Retrieve the most relevant chats based on a query."""
    results = collection.query(query_texts=[query], n_results=n)
    return [doc for sublist in results["documents"] for doc in sublist]

def generate_ai_response(user_query):
    context = retrieve_relevant_chats(user_query, n=3)
    context_text = "\n".join(context) if context else "No relevant context found."

    print(f"📜 Context Passed to AI:\n{context_text}")  # Debugging print statement

    prompt = f"Context: {context_text}\nUser: {user_query}\nAI:"
    
    response = ollama.chat(model="deepseek-r1:1.5b", messages=[{"role": "user", "content": prompt}])
    
    if "message" in response and "content" in response["message"]:
        return response["message"]["content"]
    else:
        return "I couldn't generate a response, please try again."

def process_pdf(pdf_path):
    """Extracts text from a PDF and stores it in ChromaDB."""
    with fitz.open(pdf_path) as doc:
        text = "\n".join([page.get_text() for page in doc])
    timestamp = datetime.now().isoformat()
    save_chat("PDF", text)

def upload_pdf(e):
    """Handles PDF upload."""
    file_picker.on_result = handle_pdf_upload
    file_picker.pick_files(allow_multiple=False)

def handle_pdf_upload(e):
    """Processes the uploaded PDF."""
    if e.files:
        pdf_path = e.files[0].path
        process_pdf(pdf_path)

class ChatApp(ft.Column):
    def __init__(self):
        super().__init__()
        self.chat_display = ft.Column()
        self.input_field = ft.TextField(hint_text="Enter message...")
        self.date_picker = ft.TextField(hint_text="YYYY-MM-DD", width=150)
        self.ai_toggle = ft.Checkbox(label="Ask AI")
        self.upload_button = ft.ElevatedButton("Upload PDF", on_click=upload_pdf)

        self.controls = [
            ft.Row([
                ft.Text("Chat History"),
                self.date_picker,
                ft.ElevatedButton("Retrieve", on_click=self.load_history)  # ✅ FIXED: This function is now defined
            ]),
            ft.Container(self.chat_display, height=400, width=400, border=ft.border.all(1)),
            ft.Row([
                self.input_field,
                self.ai_toggle,
                ft.ElevatedButton("Send", on_click=self.send_message),
                self.upload_button
            ])
        ]

    def send_message(self, e):
        """Handles user message sending."""
        message = self.input_field.value.strip()
        if not message:
            return  # Ignore empty messages

        # Save user message
        save_chat("User", message)
        self.chat_display.controls.append(ft.Text(f"User: {message}"))
        
        # AI Response Processing
        if self.ai_toggle.value:
            ai_response = generate_ai_response(message)
            if ai_response:
                save_chat("AI", ai_response)
                self.chat_display.controls.append(ft.Text(f"AI: {ai_response}"))
        
        # Clear input field and update display
        self.input_field.value = ""
        self.update()

    def load_history(self, e):
        """Retrieves and displays chat history for a selected date."""
        date = self.date_picker.value.strip()
        if date:
            chats = retrieve_chats_by_date(date)
            self.chat_display.controls.clear()
            for chat in chats:
                self.chat_display.controls.append(ft.Text(chat))
            self.update()

def main(page: ft.Page):
    """Main function to initialize the Flet app."""
    global file_picker
    file_picker = ft.FilePicker()
    page.overlay.append(file_picker)
    page.title = "Chat with RAG & ChromaDB"
    page.add(ChatApp())

ft.app(target=main)
