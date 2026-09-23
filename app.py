from flask import Flask, request, render_template_string, redirect, url_for, session
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'super_secret_key_123'  # Hardcoded weak secret

# Initialize DB (run once)
def init_db():
    if not os.path.exists('users.db'):
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('''CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, password TEXT)''')
        c.execute('''CREATE TABLE notes (id INTEGER PRIMARY KEY, user_id INTEGER, content TEXT)''')
        c.execute("INSERT INTO users (username, password) VALUES ('admin', 'admin123')")
        c.execute("INSERT INTO users (username, password) VALUES ('guest', 'guest')")
        conn.commit()
        conn.close()

init_db()

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('notes'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        # Vulnerable to SQL Injection
        query = f"SELECT id FROM users WHERE username = '{username}' AND password = '{password}'"
        c.execute(query)
        user = c.fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user[0]
            return redirect(url_for('notes'))
        else:
            return "Invalid credentials!"
    return '''
    <form method="post">
        Username: <input name="username"><br>
        Password: <input name="password" type="password"><br>
        <input type="submit" value="Login">
    </form>
    '''

@app.route('/notes', methods=['GET', 'POST'])
def notes():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    if request.method == 'POST':
        content = request.form['content']
        # Stored XSS possible if rendered unsafely
        c.execute("INSERT INTO notes (user_id, content) VALUES (?, ?)", (session['user_id'], content))
        conn.commit()
    
    # IDOR + SQL Injection in query param
    note_id = request.args.get('note_id', '')
    if note_id:
        # Vulnerable query
        c.execute(f"SELECT content FROM notes WHERE id = {note_id}")
        note = c.fetchone()
        if note:
            return f"<h2>Note content:</h2><p>{note[0]}</p>"  # Reflected + Stored XSS if note[0] malicious
        else:
            return "Note not found"
    
    # List own notes (but no real ownership check beyond user_id)
    c.execute("SELECT id, content FROM notes WHERE user_id = ?", (session['user_id'],))
    notes_list = c.fetchall()
    conn.close()
    
    notes_html = "<ul>"
    for n in notes_list:
        notes_html += f'<li><a href="/notes?note_id={n[0]}">{n[1][:30]}...</a></li>'
    notes_html += "</ul>"
    
    return f'''
    <h1>Your Notes</h1>
    <form method="post">
        <textarea name="content" rows="5" cols="50"></textarea><br>
        <input type="submit" value="Add Note">
    </form>
    {notes_html}
    <br><a href="/logout">Logout</a>
    '''

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)  # Debug mode ON → exposes tracebacks