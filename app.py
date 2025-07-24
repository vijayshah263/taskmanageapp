from flask import Flask, render_template, request, redirect, session, url_for, flash, jsonify
from flask_mysqldb import MySQL
import MySQLdb.cursors
from datetime import datetime
import json

app = Flask(__name__)
app.config.from_pyfile('config.py')
mysql = MySQL(app)

@app.route('/')
def home():
    return redirect('/login')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO users (username, email, password) VALUES (%s, %s, %s)", (username, email, password))
        mysql.connection.commit()
        return redirect('/login')
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cur.execute("SELECT * FROM users WHERE email=%s AND password=%s", (email, password))
        user = cur.fetchone()
        if user:
            session['loggedin'] = True
            session['id'] = user['id']
            session['username'] = user['username']
            return redirect('/dashboard')
        msg = 'Incorrect email or password'
    return render_template('login.html', msg=msg)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@app.route('/dashboard')
def dashboard():
    if 'loggedin' not in session:
        return redirect('/login')

    uid = session['id']
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT COUNT(*) as total FROM tasks WHERE user_id = %s", [uid])
    total = cur.fetchone()['total']

    cur.execute("SELECT COUNT(*) as completed FROM tasks WHERE user_id = %s AND is_completed = 1", [uid])
    completed = cur.fetchone()['completed']

    pending = total - completed

    cur.execute("SELECT COUNT(*) as overdue FROM tasks WHERE user_id=%s AND deadline < CURDATE() AND is_completed=0", [uid])
    overdue = cur.fetchone()['overdue']

    cur.execute("SELECT * FROM tasks WHERE user_id=%s AND deadline = CURDATE() AND is_completed=0", [uid])
    today = cur.fetchall()

    return render_template('dashboard.html', total=total, completed=completed, pending=pending, overdue=overdue, today=today)

@app.route('/tasks', methods=['GET', 'POST'])
def tasks():
    if 'loggedin' not in session:
        return redirect('/login')
    
    uid = session['id']
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == 'POST':
        title = request.form['title']
        category = request.form['category']
        deadline = request.form['deadline']
        cur.execute("INSERT INTO tasks (user_id, title, category, deadline, position) VALUES (%s, %s, %s, %s, %s)",
                    (uid, title, category, deadline, 0))
        mysql.connection.commit()

    cur.execute("SELECT * FROM tasks WHERE user_id = %s ORDER BY position ASC", [uid])
    tasks = cur.fetchall()
    return render_template('tasks.html', tasks=tasks)

@app.route('/update_task/<int:id>', methods=['POST'])
def update_task(id):
    title = request.form['title']
    category = request.form['category']
    deadline = request.form['deadline']
    is_completed = 1 if 'is_completed' in request.form else 0
    cur = mysql.connection.cursor()
    cur.execute("UPDATE tasks SET title=%s, category=%s, deadline=%s, is_completed=%s WHERE id=%s",
                (title, category, deadline, is_completed, id))
    mysql.connection.commit()
    return redirect('/tasks')

@app.route('/delete_task/<int:id>')
def delete_task(id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM tasks WHERE id=%s", [id])
    mysql.connection.commit()
    return redirect('/tasks')

@app.route('/reorder_tasks', methods=['POST'])
def reorder_tasks():
    data = request.get_json()
    uid = session['id']
    for i, task_id in enumerate(data['order']):
        cur = mysql.connection.cursor()
        cur.execute("UPDATE tasks SET position=%s WHERE id=%s AND user_id=%s", (i, task_id, uid))
        mysql.connection.commit()
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    app.run(debug=True)

