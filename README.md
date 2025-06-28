# CryptoBrain: AI-Powered Bitcoin Analysis Tool

CryptoBrain is a sophisticated web application built with Django that leverages the power of Large Language Models (LLMs) via the Google Gemini API to provide real-time analysis and insights on Bitcoin. Users can ask complex questions in natural language, and the system fetches, processes, and analyzes market data, news, and prices to generate a comprehensive answer.

![CryptoBrain Screenshot](placeholder.png) <!-- Sugerencia: Reemplaza esto con una captura de pantalla real de tu app -->

## Features

-   **Real-Time Data**: Fetches up-to-the-minute Bitcoin prices and market news from external APIs.
-   **AI-Powered Analysis**: Uses an AI agent (LangChain + Google Gemini) to interpret data and answer user queries.
-   **Asynchronous Backend**: Built with async views in Django for high performance and non-blocking I/O.
-   **Standalone Executable**: Packaged with PyInstaller for easy distribution and execution on Windows without needing a Python environment.

## Technologies Used

-   **Backend**: Django 5.1
-   **Web Server**: Waitress
-   **AI / LLMs**: LangChain, Google Gemini API
-   **Async Networking**: aiohttp
-   **Data Validation**: Pydantic
-   **Packaging**: PyInstaller

---

## Project Setup

### 1. Prerequisites

-   Python 3.10+
-   Git

### 2. Clone the Repository

```bash
git clone <YOUR_REPOSITORY_URL>
cd CryptoBrain
```

### 3. Create and Activate Virtual Environment

```bash
# On Windows
python -m venv venv
venv\Scripts\activate

# On macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure Environment Variables

Create a `.env` file inside the `cryptobrain` directory (next to `run.py`). Add your API keys:

```dotenv
# .env file
CRYPTOPANIC_API_KEY="YOUR_CRYPTOPANIC_API_KEY"
GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
```

### 6. Run Database Migrations

```bash
python cryptobrain/manage.py migrate
```

---

## How to Run

### Development Mode

To run the application with the Django development server (ideal for coding and debugging):

```bash
python cryptobrain/manage.py runserver
```

The app will be available at `http://127.0.0.1:8000/`.

### Production Mode (using Waitress)

To run the application using the production-ready Waitress server (as the executable does):

```bash
python cryptobrain/run.py
```

---

## Building the Windows Executable

This project is configured to be packaged into a standalone Windows executable using PyInstaller.

### 1. Collect Static Files

Before building, you must collect all of Django's static files into a single directory.

```bash
python cryptobrain/manage.py collectstatic --noinput
```

### 2. Run PyInstaller

Use the provided `.spec` file, which contains all the necessary configurations.

```bash
pyinstaller cryptobrain/run.spec
```

### 3. Find the Executable

Once the build is complete, you will find a folder named `CryptoBrain` inside the `cryptobrain/dist/` directory. You can compress this folder into a `.zip` file for distribution.

To run the application, simply double-click on `CryptoBrain.exe` inside that folder.