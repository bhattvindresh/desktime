# Mini Project Report Notes

## Title
TimeTrack Pro: Real-Time Employee Time Tracking and Productivity Dashboard

## Abstract
TimeTrack Pro is a web-based employee time tracking system designed to record work sessions and display updates in real time. Employees can start and stop timers, while the dashboard summarizes tracked time and recent activity. The system uses Flask for server-side routing, SQLite for persistence, and Socket.IO for real-time communication.

## Objectives
1. Build a simple employee time tracking interface.
2. Store work sessions in a relational database.
3. Display session duration and daily summaries.
4. Broadcast session changes to connected dashboards.
5. Provide separate administrator and employee demo roles.

## Modules
- Authentication module
- Employee time tracker
- Session management API
- Real-time notification module
- Dashboard and reporting module

## Database design
### User
- id (primary key)
- name
- email
- password_hash
- role

### WorkSession
- id (primary key)
- user_id (foreign key)
- started_at
- ended_at
- status
- activity

## Future enhancements
- Desktop agent for automatic active/idle detection with user consent
- Project and task assignment
- CSV/PDF reports
- Team and department management
- Configurable work schedules and attendance rules
- Optional screenshot capture with transparent consent and retention controls

## Suggested demonstration
1. Sign in as the employee and start a timer.
2. Sign in as the admin in a second browser.
3. Observe the live session update.
4. Stop the employee timer.
5. Show the completed session and duration in the history table.
