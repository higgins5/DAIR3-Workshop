"""
HelperGUI.py
GUI chatbot interface using the OpenAI API and assistant capabilities.
Configuration is dynamically loaded from a JSON file with user and assistant properties.
Includes support for file uploads and persistent threaded interactions.

By Juan B. Gutiérrez, Professor of Mathematics 
University of Texas at San Antonio.

License: Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)
"""
import os
import openai
import json
import sys
import io
import glob
import argparse
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLineEdit, QVBoxLayout, QPushButton,
    QHBoxLayout, QLabel, QComboBox, QProgressBar
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QUrl
from PyQt5.QtGui import QDragEnterEvent, QDropEvent, QClipboard, QFont
from md_widget import MarkdownTextEdit
from md_loader import load_persona
from file_upload_worker import FileUploadWorker, format_usage

# Force UTF-8 encoding for stdout and stderr
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

class LLMWorker(QThread):
    # Define a signal to emit when the assistant's response is ready
    result_ready = pyqtSignal(str)

    def __init__(self, user_input, chatbot):
        super().__init__()
        self.user_input = user_input
        self.chatbot = chatbot  # owns client, model, instructions, conversation state

    def run(self):
        try:
            kwargs = {
                "model": self.chatbot.model,
                "instructions": self.chatbot.instructions,
                "input": self.user_input,
            }
            if self.chatbot.previous_response_id:
                kwargs["previous_response_id"] = self.chatbot.previous_response_id
            if self.chatbot.vector_store_id:
                kwargs["tools"] = [{
                    "type": "file_search",
                    "vector_store_ids": [self.chatbot.vector_store_id],
                }]

            response = self.chatbot.client.responses.create(**kwargs)
            self.chatbot.previous_response_id = response.id
            self.result_ready.emit(response.output_text)
        except Exception as e:
            self.result_ready.emit(f"Error: {e}")

class OpenAIChatbot(QWidget):
    def __init__(self, role_md_path="general.md"):
        super().__init__()

        # Load configuration from CONFIG section
        config_file = "config.json"
        with open(config_file, 'r', encoding='utf-8') as file:
            raw_config = json.load(file)
            config = raw_config['CONFIG']

        # Extract configuration values
        self.user = config['user']
        self.name = config['name']

        # Build instructions from common.md + role markdown with variable substitution
        self.common_md = config.get('common_md', 'common.md')
        self.role_md = role_md_path
        self.instructions = load_persona(self.common_md, self.role_md, {
            "user": self.user,
            "name": self.name,
        })
        self.model = config['model']
        self.font_size = int(config.get('fontsize', 12))
        self.loaded_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.latest_response = ""

        # Load API key from environment
        openai.api_key = os.getenv("OPENAI_API_KEY")
        if not openai.api_key:
            print("API key is not set. Please set the OPENAI_API_KEY environment variable.")
            exit(1)

        # Create OpenAI API client
        self.client = openai.OpenAI()

        # Responses API conversation pointer; updated after every successful turn.
        self.previous_response_id = None

        # Vector store backing the file_search tool; created lazily on first upload.
        self.vector_store_id = None

        # Set up the GUI interface
        self.init_gui()

    def init_gui(self):
        # Set up main window parameters
        self.setWindowTitle("JuanGPT")
        self.setGeometry(100, 100, 700, 500)
        self.setAcceptDrops(True)  # Enable drag and drop

        layout = QVBoxLayout()

        # --- Header row: Role dropdown (left) + Font +/- (right) ---
        header = QHBoxLayout()
        header.addWidget(QLabel("Role:"))
        self.role_combo = QComboBox()
        self.role_combo.addItems(self._discover_md_files())
        if self.role_md in [self.role_combo.itemText(i) for i in range(self.role_combo.count())]:
            self.role_combo.setCurrentText(self.role_md)
        self.role_combo.currentTextChanged.connect(self.on_role_changed)
        header.addWidget(self.role_combo, 1)
        header.addStretch()
        self.font_dec_btn = QPushButton("-")
        self.font_dec_btn.setFixedWidth(32)
        self.font_dec_btn.clicked.connect(lambda: self.apply_font_size(self.font_size - 1))
        self.font_inc_btn = QPushButton("+")
        self.font_inc_btn.setFixedWidth(32)
        self.font_inc_btn.clicked.connect(lambda: self.apply_font_size(self.font_size + 1))
        header.addWidget(self.font_dec_btn)
        header.addWidget(self.font_inc_btn)
        layout.addLayout(header)

        # Status row (spinner + label) shown while a file upload runs. Hidden when idle.
        self.status_row = QWidget()
        status_layout = QHBoxLayout(self.status_row)
        status_layout.setContentsMargins(0, 0, 0, 0)
        self.upload_progress = QProgressBar()
        self.upload_progress.setRange(0, 0)
        self.upload_progress.setFixedWidth(140)
        self.upload_progress.setTextVisible(False)
        self.upload_status_label = QLabel("")
        status_layout.addWidget(self.upload_progress)
        status_layout.addWidget(self.upload_status_label, 1)
        self.status_row.setVisible(False)
        layout.addWidget(self.status_row)
        self.upload_worker = None

        # Text display area for messages (renders Markdown via setMarkdown)
        self.text_area = MarkdownTextEdit(self)
        layout.addWidget(self.text_area)

        # Display session header
        self.text_area.append(f"**Model:** `{self.model}` (OpenAI) — **Loaded:** {self.loaded_at}")
        self.text_area.append(f"**Agent:** {self.name} — **Role:** {self.role_md}")
        self.text_area.append("<<<<<<<<<<<<<<<<<<<<<<<<<<")

        # User input field
        self.user_input = QLineEdit(self)
        self.user_input.setPlaceholderText("Type your message and press Enter")
        layout.addWidget(self.user_input)

        # Button to copy latest assistant response
        self.copy_button = QPushButton("Copy Latest Answer")
        self.copy_button.clicked.connect(self.copy_latest_answer)
        layout.addWidget(self.copy_button)

        # Bind Enter key to user input processing
        self.user_input.returnPressed.connect(self.on_enter_pressed)

        # Apply layout to the window
        self.setLayout(layout)

        # Apply initial font size to everything
        self.apply_font_size(self.font_size)

    def _discover_md_files(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        files = sorted(os.path.basename(p) for p in glob.glob(os.path.join(script_dir, "*.md")))
        return [f for f in files if f != "common.md"]

    def apply_font_size(self, size):
        self.font_size = max(6, min(48, int(size)))
        font = QFont()
        font.setPointSize(self.font_size)
        for child in self.findChildren(QWidget):
            child.setFont(font)
        self.text_area.document().setDefaultFont(font)
        self.text_area.rerender()

    def on_role_changed(self, role):
        if not role or role == self.role_md:
            return
        self.role_md = role
        self.instructions = load_persona(self.common_md, self.role_md, {
            "user": self.user,
            "name": self.name,
        })
        # Reset Responses API chain so the new role doesn't carry old context.
        self.previous_response_id = None
        self.text_area.clear()
        self.text_area.append(f"**Model:** `{self.model}` (OpenAI) — **Loaded:** {self.loaded_at}")
        self.text_area.append(f"**Agent:** {self.name} — **Role changed to:** {self.role_md}")
        self.text_area.append("<<<<<<<<<<<<<<<<<<<<<<<<<<")

    def dragEnterEvent(self, event: QDragEnterEvent):
        # Accept drag event if a file is present
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        # Handle file drop by extracting path
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            self.upload_file(file_path)

    def upload_file(self, file_path):
        """Drag-and-drop entry. Runs on a background QThread so the GUI shows
        a live spinner + status label instead of freezing."""
        if self.upload_worker is not None and self.upload_worker.isRunning():
            self.text_area.append(f"_(Already uploading; ignored drop of `{file_path}`)_")
            return

        filename = os.path.basename(file_path)
        client = self.client
        name = self.name

        def do_upload(status_cb):
            status_cb("Uploading file to OpenAI (remote)")
            with open(file_path, 'rb') as file_data:
                file_object = client.files.create(file=file_data, purpose='assistants')
            file_id = file_object.id

            status_cb("Indexing in vector store (remote)")
            if self.vector_store_id is None:
                vs = client.vector_stores.create(name=f"{name}_files")
                self.vector_store_id = vs.id
            client.vector_stores.files.create_and_poll(
                vector_store_id=self.vector_store_id,
                file_id=file_id,
            )
            return f"File uploaded and indexed. ID: `{file_id}`", None

        self.text_area.append(f"**Processing file:** `{filename}`")
        self.text_area.append(">>>>>>>>>>>>>>>>>>>>>>>>>>")
        self._show_upload_status("Starting upload…")

        self.upload_worker = FileUploadWorker(do_upload)
        self.upload_worker.status.connect(self._on_upload_status)
        self.upload_worker.finished_ok.connect(self._on_upload_finished)
        self.upload_worker.finished_err.connect(self._on_upload_error)
        self.upload_worker.start()

    def _show_upload_status(self, msg):
        self.upload_status_label.setText(msg)
        self.status_row.setVisible(True)

    def _hide_upload_status(self):
        self.status_row.setVisible(False)
        self.upload_status_label.setText("")

    def _on_upload_status(self, msg):
        self._show_upload_status(msg)
        self.text_area.append(f"_…{msg}_")

    def _on_upload_finished(self, response, usage):
        usage_str = format_usage(usage) if usage else ""
        if usage_str:
            self.text_area.append(f"_Done — tokens: {usage_str}_")
        else:
            self.text_area.append("_Done._")
        self._hide_upload_status()
        self.text_area.append(response)
        self.text_area.append("<<<<<<<<<<<<<<<<<<<<<<<<<<")

    def _on_upload_error(self, msg):
        self._hide_upload_status()
        self.text_area.append(f"**Upload error:** {msg}")
        self.text_area.append("<<<<<<<<<<<<<<<<<<<<<<<<<<")

    def on_enter_pressed(self):
        # Process input when Enter is pressed
        user_input = self.user_input.text().strip()
        if user_input:
            self.process_user_input(user_input)
        self.user_input.clear()

    def process_user_input(self, user_input):
        # Display user input
        self.text_area.append(f"{self.user}: {user_input}")
        self.text_area.append(">>>>>>>>>>>>>>>>>>>>>>>>>>")
        self.user_input.setEnabled(False)

        # Launch worker thread to handle assistant response
        self.worker_thread = LLMWorker(user_input, self)
        self.worker_thread.result_ready.connect(self.display_results)
        self.worker_thread.start()

    def display_results(self, response):
        # Show assistant response
        self.latest_response = response
        self.text_area.append(f"{self.name}: {response}")
        self.text_area.append("<<<<<<<<<<<<<<<<<<<<<<<<<<")
        self.user_input.setEnabled(True)

    def copy_latest_answer(self):
        # Copy latest assistant message to clipboard
        clipboard = QApplication.clipboard()
        clipboard.setText(self.latest_response)
        self.text_area.append("Latest answer copied to clipboard.")

# Start the GUI application
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Single-OpenAI-agent chat GUI.")
    parser.add_argument(
        "role_md",
        nargs="?",
        default="general.md",
        help="Path to a role markdown file (default: general.md). Examples: researcher.md, grant_writer_NIH.md, article_reviewer.md.",
    )
    args = parser.parse_args()

    app = QApplication([])
    chatbot = OpenAIChatbot(role_md_path=args.role_md)
    chatbot.show()
    app.exec_()
