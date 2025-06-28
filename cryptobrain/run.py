import os
import webbrowser
from waitress import serve

print("--- CryptoBrain Dashboard: Starting ---")

try:
    # Set the Django settings module environment variable
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cryptobrain.settings')
    print("DJANGO_SETTINGS_MODULE set to 'cryptobrain.settings'")

    from cryptobrain.wsgi import application
    print("Successfully imported Django WSGI application.")

    # Define host and port
    host = '127.0.0.1'
    port = 8000
    url = f"http://{host}:{port}"

    print(f"Starting production server with Waitress at {url}")
    print("The application will open in your default browser shortly.")
    print("Press Ctrl+C in this window to exit.")

    # Open the URL in the default web browser
    webbrowser.open(url)

    # Serve the Django application
    serve(application, host=host, port=port)

except Exception as e:
    print("--- FATAL ERROR DURING STARTUP ---")
    print(f"An error occurred: {e}")
    # In a real production environment, you would log this to a file.
    # The input() call will pause the console window so you can read the error.
    input("Press Enter to exit.")
