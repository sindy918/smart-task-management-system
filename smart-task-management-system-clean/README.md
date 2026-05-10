# Smart Task Management System

A robust, full-stack Task Management System built with Python Flask, PostgreSQL, and real-time WebSockets. This application allows users to manage their daily tasks efficiently while providing insightful analytics and live notifications.

## 🚀 Features

- **User Authentication**: Secure registration, login, and logout functionality.
- **Task Management**: Full CRUD operations (Add, Update, Delete, View) for tasks.
- **Real-time Notifications**: Instant updates when tasks are modified, powered by Flask-SocketIO.
- **Task Analytics**: Visual summary of total, completed, and pending tasks using Pandas and NumPy.
- **Modern UI**: A premium, responsive dashboard with glassmorphism aesthetics.

## 🛠️ Tech Stack

- **Backend**: Python, Flask, Flask-SocketIO, Flask-Login
- **Database**: PostgreSQL (via Psycopg2)
- **Data Processing**: Pandas, NumPy
- **Frontend**: HTML5, CSS3 (Vanilla), JavaScript (Vanilla)
- **Icons**: Lucide-Icons

## 📋 Prerequisites

- Python 3.8+
- PostgreSQL installed and running
- A database named `smart_task_db` created in PostgreSQL

## ⚙️ Setup Instructions

### 1. Clone the repository
```bash
git clone <your-repo-link>
cd smart-task-management
```

### 2. Install dependencies
It is recommended to use a virtual environment:
```bash
python -m venv venv
source venv/Scripts/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Create a `.env` file in the root directory (or edit the existing one) with your PostgreSQL credentials:
```env
DB_NAME=smart_task_db
DB_USER=postgres
DB_PASS=your_password
DB_HOST=localhost
DB_PORT=5432
SECRET_KEY=your_secret_key
```

### 4. Initialize the Database
Run the following command to create the necessary tables:
```bash
python database.py
```

### 5. Run the Application
Start the Flask development server:
```bash
python app.py
```
The application will be available at `http://127.0.0.1:5000`.

## 🗃️ Database Schema

The system uses two main tables:
1. `users`: Stores user credentials and profile information.
2. `tasks`: Stores task details, priorities, and statuses, linked to the user.

Refer to [schema.sql](schema.sql) for full SQL definitions.

## 📊 Analytics Logic
The analytics engine uses **Pandas** to process task data directly from the PostgreSQL database, calculating:
- Total task count
- Completion rate
- Pending vs. Completed ratio

## 🔔 WebSocket Implementation
The application uses **Flask-SocketIO** to broadcast events to all connected clients when a task is created, updated, or deleted, ensuring a collaborative and live experience.
