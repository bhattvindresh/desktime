# TimeTrack Pro — DeskTime-inspired Final Year Mini Project

A real-time employee time-tracking dashboard built with Python Flask, SQLite, Flask-SocketIO, HTML, CSS and JavaScript.

## Features
- Login with Admin and Employee demo accounts
- Start and stop work sessions
- Live session duration counter
- Real-time session update broadcasts using Socket.IO
- Today's tracked-time summary and active timer count
- Recent session history
- Responsive dashboard
- SQLite database created automatically

## Requirements
- Python 3.9+
- Internet connection for the Socket.IO browser client and optional Google Fonts CDN

## Run locally

### 1. Extract the ZIP and open a terminal in the project folder

### 2. Create a virtual environment
```bash
python -m venv venv
```

Activate it:
- Windows: `venv\Scripts\activate`
- macOS/Linux: `source venv/bin/activate`

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Start the application
```bash
python app.py
```

### 5. Open in your browser
http://127.0.0.1:5000

## Demo login
| Role | Email | Password |
|---|---|---|
| Admin | admin@demo.com | admin123 |
| Employee | employee@demo.com | employee123 |

Open the application in two browsers (one as Admin and one as Employee) to demonstrate live session updates.

## Project structure
```text
desktime_mini_project/
├── app.py
├── requirements.txt
├── README.md
├── templates/
│   ├── login.html
│   └── dashboard.html
└── static/
    ├── app.js
    └── style.css
```

## Technology stack
- Frontend: HTML5, CSS3, JavaScript
- Backend: Python Flask
- Real-time communication: Socket.IO
- Database: SQLite
- Authentication: Flask session + Werkzeug password hashing

## Important scope and limitations
This is an educational DeskTime-inspired mini project, not a production clone. It tracks sessions when an employee explicitly starts and stops the timer. It does not collect screenshots, keystrokes, browser history, or background application usage. Productivity scoring and payroll calculations are intentionally not claimed as implemented.

Before deployment, change the Flask secret key, use HTTPS, add CSRF protection, apply stricter authorization to Socket.IO rooms, configure production hosting, and obtain informed employee consent for any additional monitoring features.
