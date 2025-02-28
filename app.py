from flask import Flask, render_template, request, redirect, url_for
import json
import os
from sklearn.linear_model import LinearRegression
import numpy as np
from datetime import datetime, timedelta
import uuid

app = Flask(__name__)

TASKS_FILE = 'tasks.json'
INVITE_FILE = 'invite.json'

def load_tasks():
    print("Loading tasks...")
    if os.path.exists(TASKS_FILE):
        try:
            with open(TASKS_FILE, 'r') as f:
                data = json.load(f)
            print("Tasks file read")
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading tasks.json: {e}. Starting fresh.")
            return [], []
        if isinstance(data, list):  # Old list format
            active_tasks = []
            done_tasks = []
            for task_data in data:
                if len(task_data) == 5:
                    task_tuple = (task_data[0], task_data[1], task_data[2], task_data[3], task_data[4], "Unknown")
                elif len(task_data) == 4:
                    task_tuple = (task_data[0], task_data[1], task_data[2], task_data[3], datetime.now().isoformat(), "Unknown")
                elif len(task_data) == 3:
                    task_tuple = (task_data[0], task_data[1], task_data[2], False, datetime.now().isoformat(), "Unknown")
                else:
                    task_tuple = tuple(task_data)
                if len(task_tuple) == 6 and task_tuple[3]:
                    done_tasks.append(task_tuple)
                else:
                    active_tasks.append(task_tuple)
            print("Tasks parsed (old format)")
            return active_tasks, done_tasks
        active_tasks = []
        done_tasks = data.get('done_tasks', [])
        for task_data in data.get('active_tasks', []):
            if len(task_data) == 5:
                active_tasks.append((task_data[0], task_data[1], task_data[2], task_data[3], task_data[4], "Unknown"))
            elif len(task_data) == 4:
                active_tasks.append((task_data[0], task_data[1], task_data[2], task_data[3], datetime.now().isoformat(), "Unknown"))
            elif len(task_data) == 3:
                active_tasks.append((task_data[0], task_data[1], task_data[2], False, datetime.now().isoformat(), "Unknown"))
            else:
                active_tasks.append(tuple(task_data))
        for task_data in data.get('done_tasks', []):
            if len(task_data) == 5:
                done_tasks.append((task_data[0], task_data[1], task_data[2], task_data[3], task_data[4], "Unknown"))
            elif len(task_data) == 4:
                done_tasks.append((task_data[0], task_data[1], task_data[2], task_data[3], datetime.now().isoformat(), "Unknown"))
            elif len(task_data) == 3:
                done_tasks.append((task_data[0], task_data[1], task_data[2], True, datetime.now().isoformat(), "Unknown"))
            else:
                done_tasks.append(tuple(task_data))
        print("Tasks parsed")
        return active_tasks, done_tasks
    print("No tasks file, starting fresh")
    return [], []

def save_tasks(active_tasks, done_tasks):
    with open(TASKS_FILE, 'w') as f:
        json.dump({'active_tasks': active_tasks, 'done_tasks': done_tasks}, f)

def load_invite_data():
    print("Loading invite data...")
    if os.path.exists(INVITE_FILE):
        with open(INVITE_FILE, 'r') as f:
            data = json.load(f)
        print("Invite data read")
        return data.get('code', None), data.get('owner_source', "Unknown"), data.get('invitee_source', "Unknown")
    print("No invite file")
    return None, "Unknown", "Unknown"

def save_invite_data(code, owner_source, invitee_source):
    with open(INVITE_FILE, 'w') as f:
        json.dump({'code': code, 'owner_source': owner_source, 'invitee_source': invitee_source}, f)

def update_priorities(tasks):
    now = datetime.now()
    updated_tasks = []
    for task, priority, est_time, completed, created_at, source in tasks:
        created_date = datetime.fromisoformat(created_at)
        age_days = (now - created_date).days
        new_priority = priority
        if not completed and age_days > 0 and priority < 5:
            new_priority = min(priority + age_days, 5)
        updated_tasks.append((task, new_priority, est_time, completed, created_at, source))
    return updated_tasks

print("Starting initialization...")
active_tasks, done_tasks = load_tasks()
print("Tasks loaded")
invite_code, owner_source, invitee_source = load_invite_data()
print("Invite data loaded")
if not invite_code:
    invite_code = str(uuid.uuid4())[:8].upper()
    owner_source = "Unknown"
    invitee_source = "Unknown"
    save_invite_data(invite_code, owner_source, invitee_source)
    print("New invite data saved")

default_X = np.array([[1], [2], [3], [4], [5]])
default_y = np.array([15, 30, 45, 60, 90])
model = LinearRegression()
model.fit(default_X, default_y)
print("Model trained")

@app.route('/', methods=['GET', 'POST'])
def home():
    global active_tasks, done_tasks, model, invite_code, owner_source, invitee_source
    message = None
    if request.method == 'POST':
        if 'task' in request.form:
            task = request.form['task']
            priority = int(request.form['priority'])
            est_time = int(request.form['est_time'])
            active_tasks.append((task, priority, est_time, False, datetime.now().isoformat(), owner_source))
            save_tasks(active_tasks, done_tasks)
            message = "Task added successfully!"
        elif 'toggle' in request.form:
            index = int(request.form['toggle'])
            task, priority, est_time, completed, created_at, source = active_tasks[index]
            if not completed:
                done_tasks.append((task, priority, est_time, True, created_at, source))
                del active_tasks[index]
            save_tasks(active_tasks, done_tasks)
        elif 'regenerate' in request.form:
            invite_code = str(uuid.uuid4())[:8].upper()
            save_invite_data(invite_code, owner_source, invitee_source)
            message = "New invite code generated!"
        elif 'set_source' in request.form:
            owner_source = request.form['source'] or "Unknown"
            save_invite_data(invite_code, owner_source, invitee_source)
            message = "Source name updated!"
        if len(active_tasks) >= 5:
            X_train = np.array([[t[1]] for t in active_tasks])
            y_train = np.array([t[2] for t in active_tasks])
            temp_model = LinearRegression()
            temp_model.fit(X_train, y_train)
            r2 = temp_model.score(X_train, y_train)
            if r2 > 0.5:
                model = temp_model
    active_tasks = update_priorities(active_tasks)
    save_tasks(active_tasks, done_tasks)
    sorted_active = []
    for i, (task, priority, est_time, completed, created_at, source) in enumerate(active_tasks):
        pred_time = model.predict(np.array([[priority]]))[0]
        sorted_active.append((task, priority, est_time, pred_time, completed, i, created_at, source))
    sorted_active.sort(key=lambda x: -x[1])
    sorted_done = [(t[0], t[1], t[2], model.predict(np.array([[t[1]]]))[0], t[3], i, t[4], t[5]) 
                   for i, t in enumerate(done_tasks)]
    return render_template('index.html', active_tasks=sorted_active, done_tasks=sorted_done, invite_code=invite_code, owner_source=owner_source, message=message)

@app.route('/add/<code>', methods=['GET', 'POST'])
def add_task(code):
    global active_tasks, done_tasks, model, invite_code, invitee_source
    if code != invite_code:
        return "Invalid invite code", 403
    message = None
    if request.method == 'POST':
        if 'task' in request.form:
            task = request.form['task']
            priority = int(request.form['priority'])
            est_time = int(request.form['est_time'])
            active_tasks.append((task, priority, est_time, False, datetime.now().isoformat(), invitee_source))
            save_tasks(active_tasks, done_tasks)
            message = "Task added successfully!"
        elif 'set_source' in request.form:
            invitee_source = request.form['source'] or "Unknown"
            save_invite_data(invite_code, owner_source, invitee_source)
            message = "Source name updated!"
    sorted_active = []
    for i, (task, priority, est_time, completed, created_at, source) in enumerate(active_tasks):
        pred_time = model.predict(np.array([[priority]]))[0]
        sorted_active.append((task, priority, est_time, pred_time, completed, i, created_at, source))
    sorted_active.sort(key=lambda x: -x[1])
    sorted_done = [(t[0], t[1], t[2], model.predict(np.array([[t[1]]]))[0], t[3], i, t[4], t[5]) 
                   for i, t in enumerate(done_tasks)]
    return render_template('add.html', code=code, active_tasks=sorted_active, done_tasks=sorted_done, invitee_source=invitee_source, message=message)

if __name__ == "__main__":
    print("Starting server...")
    app.run(host='0.0.0.0', port=5000, debug=True)