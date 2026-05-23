"""
agentClaude.py
Single-agent chat GUI seeded with Anthropic Claude. Uses the shared
SingleAgentGUI from single_agent_gui.py: Provider + Model dropdowns, unified
file drop (Context or RAG), per-agent knowledge base, role switcher.

CLI:
    python agentClaude.py                  # default role: general.md
    python agentClaude.py researcher.md
    python agentClaude.py grant_writer_NIH.md

By Juan B. Gutiérrez, Professor of Mathematics
University of Texas at San Antonio.

License: Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)
"""
import argparse
<<<<<<< HEAD
from single_agent_gui import launch
=======
import base64
import mimetypes
from datetime import datetime
import anthropic
<<<<<<< HEAD
=======
import google 
from google import genai
from google.genai import types
>>>>>>> 4d036c6 (preworkshop analysis updates, modified agent scripts)
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLineEdit, QVBoxLayout, QPushButton,
    QHBoxLayout, QLabel, QComboBox, QProgressBar
)
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QDragEnterEvent, QDropEvent, QFont
from md_widget import MarkdownTextEdit
from md_loader import load_persona
from file_upload_worker import FileUploadWorker, format_usage
>>>>>>> db0e051 (added FOO files, chats, agents, config, README, etc. that were missing)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Single-Claude-agent chat GUI.")
    parser.add_argument(
        "role_md",
        nargs="?",
        default="general.md",
        help="Path to a role markdown file (default: general.md). Examples: researcher.md, grant_writer_NIH.md, article_reviewer.md.",
    )
    args = parser.parse_args()
    launch(preferred_provider="anthropic", window_title="JuanClaude", role_md=args.role_md)
