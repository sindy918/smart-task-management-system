import eventlet
eventlet.monkey_patch()
import os
import pandas as pd
import numpy as np
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_socketio import SocketIO, emit
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db_connection, init_db
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "default-secret-key")
socketio = SocketIO(app, cors_allowed_origins="*")

# Login Manager setup
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

class User(UserMixin):
    def __init__(self, id, username, email):
        self.id = id
        self.username = username
        self.email = email

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    if not conn:
        return None
    cur = conn.cursor()
    cur.execute("SELECT id, username, email FROM users WHERE id = %s", (user_id,))
    user_data = cur.fetchone()
    cur.close()
    conn.close()
    if user_data:
        return User(user_data[0], user_data[1], user_data[2])
    return None

# --- Auth Routes ---

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        hashed_password = generate_password_hash(password)
        
        conn = get_db_connection()
        if not conn:
            flash("Database connection error")
            return redirect(url_for('register'))
            
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO users (username, email, password) VALUES (%s, %s, %s)", 
                        (username, email, hashed_password))
            conn.commit()
            flash("Registration successful! Please login.")
            return redirect(url_for('login'))
        except Exception as e:
            conn.rollback()
            flash("User already exists or error occurred.")
            return redirect(url_for('register'))
        finally:
            cur.close()
            conn.close()
            
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = get_db_connection()
        if not conn:
            flash("Database connection error")
            return redirect(url_for('login'))
            
        cur = conn.cursor()
        cur.execute("SELECT id, username, email, password FROM users WHERE username = %s", (username,))
        user_data = cur.fetchone()
        cur.close()
        conn.close()
        
        if user_data and check_password_hash(user_data[3], password):
            user = User(user_data[0], user_data[1], user_data[2])
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid username or password")
            
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# --- Task Routes ---

@app.route('/')
@login_required
def dashboard():
    conn = get_db_connection()
    tasks = []
    if conn:
        cur = conn.cursor()
        cur.execute("SELECT id, title, description, priority, status, created_date FROM tasks WHERE user_id = %s ORDER BY created_date DESC", (current_user.id,))
        rows = cur.fetchall()
        for row in rows:
            tasks.append({
                'id': row[0],
                'title': row[1],
                'description': row[2],
                'priority': row[3],
                'status': row[4],
                'created_date': row[5].strftime("%Y-%m-%d %H:%M:%S")
            })
        cur.close()
        conn.close()
        
    analytics = {'total': 0, 'completed': 0, 'pending': 0, 'percentage': 0}
    if tasks:
        df = pd.DataFrame(tasks)
        total_tasks = len(df)
        completed_tasks = len(df[df['status'] == 'Completed'])
        pending_tasks = total_tasks - completed_tasks
        completion_percentage = np.divide(completed_tasks, total_tasks) * 100
        analytics = {
            'total': int(total_tasks),
            'completed': int(completed_tasks),
            'pending': int(pending_tasks),
            'percentage': round(float(completion_percentage), 2)
        }
        
    return render_template('dashboard.html', tasks=tasks, analytics=analytics)

@app.route('/api/tasks', methods=['POST'])
@login_required
def add_task():
    data = request.json
    title = data.get('title')
    description = data.get('description')
    priority = data.get('priority', 'Medium')
    
    conn = get_db_connection()
    if conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO tasks (user_id, title, description, priority) VALUES (%s, %s, %s, %s) RETURNING id", 
                    (current_user.id, title, description, priority))
        task_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        
        # Emit real-time notification
        socketio.emit('task_update', {'message': f'New task added: {title}'})
        
        return jsonify({'status': 'success', 'task_id': task_id})
    return jsonify({'status': 'error'}), 500

@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
@login_required
def update_task(task_id):
    data = request.json
    status = data.get('status')
    
    conn = get_db_connection()
    if conn:
        cur = conn.cursor()
        cur.execute("UPDATE tasks SET status = %s WHERE id = %s AND user_id = %s", (status, task_id, current_user.id))
        conn.commit()
        cur.close()
        conn.close()
        
        # Emit real-time notification
        socketio.emit('task_update', {'message': f'Task status updated to {status}'})
        
        return jsonify({'status': 'success'})
    return jsonify({'status': 'error'}), 500

@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
@login_required
def delete_task(task_id):
    conn = get_db_connection()
    if conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM tasks WHERE id = %s AND user_id = %s", (task_id, current_user.id))
        conn.commit()
        cur.close()
        conn.close()
        
        # Emit real-time notification
        socketio.emit('task_update', {'message': 'Task deleted successfully'})
        
        return jsonify({'status': 'success'})
    return jsonify({'status': 'error'}), 500

# --- Analytics API ---

@app.route('/api/analytics')
@login_required
def analytics():
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'db connection failed'}), 500
    cur = conn.cursor()
    try:
        cur.execute("SELECT status FROM tasks WHERE user_id = %s", (current_user.id,))
        rows = cur.fetchall()
        df = pd.DataFrame(rows, columns=['status'])
    finally:
        cur.close()
        conn.close()
    
    total_tasks = len(df)
    if total_tasks == 0:
        return jsonify({
            'total': 0,
            'completed': 0,
            'pending': 0,
            'percentage': 0
        })
        
    completed_tasks = len(df[df['status'] == 'Completed'])
    pending_tasks = total_tasks - completed_tasks
    
    # Using NumPy to calculate percentage
    completion_percentage = np.divide(completed_tasks, total_tasks) * 100
    
    return jsonify({
        'total': int(total_tasks),
        'completed': int(completed_tasks),
        'pending': int(pending_tasks),
        'percentage': round(float(completion_percentage), 2)
    })

if __name__ == '__main__':
    # Initialize DB tables if they don't exist
    init_db()
    socketio.run(app, debug=True)
