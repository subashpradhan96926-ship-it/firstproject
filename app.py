from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "my_secret_key_change_this"
# ADMIN EMAIL
ADMIN_EMAIL = "your_email@gmail.com"

DATABASE = os.path.join(app.root_path, "database.db")


# DATABASE CONNECTION
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# CREATE DATABASE TABLES
def create_table():

    conn = get_db_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            task TEXT NOT NULL,
            completed INTEGER DEFAULT 0,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()


# HOME
@app.route("/")
def home():
    return render_template("index.html")


# REGISTER
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        hashed_password = generate_password_hash(password)

        conn = get_db_connection()

        try:
            conn.execute(
                "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
                (name, email, hashed_password)
            )

            conn.commit()
            flash("Registration successful!")
            return redirect(url_for("login"))

        except sqlite3.IntegrityError:
            flash("Email already registered!")

        finally:
            conn.close()

    return render_template("register.html")


# LOGIN
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        conn = get_db_connection()

        user = conn.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        conn.close()

        if user and check_password_hash(user["password"], password):

            session.clear()
            session["user_id"] = user["id"]
            session["name"] = user["name"]

            return redirect(url_for("dashboard"))

        flash("Invalid email or password!")

    return render_template("login.html")


# GET USER TASKS
def get_tasks(user_id):

    conn = get_db_connection()

    tasks = conn.execute(
        "SELECT * FROM tasks WHERE user_id = ? ORDER BY id DESC",
        (user_id,)
    ).fetchall()

    conn.close()

    return tasks


# DASHBOARD
@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()

    user = conn.execute(
        "SELECT id, name, email FROM users WHERE id = ?",
        (session["user_id"],)
    ).fetchone()

    conn.close()

    if user is None:
        session.clear()
        return redirect(url_for("login"))

    tasks = get_tasks(session["user_id"])

    return render_template(
        "dashboard.html",
        tasks=tasks,
        user=user
    )

# EDIT PROFILE
@app.route("/update-profile", methods=["POST"])
def update_profile():

    if "user_id" not in session:
        return redirect(url_for("login"))

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()

    if not name or not email:
        flash("Name and email are required!")
        return redirect(url_for("dashboard"))

    conn = get_db_connection()

    try:

        conn.execute(
            """
            UPDATE users
            SET name = ?, email = ?
            WHERE id = ?
            """,
            (name, email, session["user_id"])
        )

        conn.commit()

        session["name"] = name

        flash("Profile updated successfully!")

    except sqlite3.IntegrityError:

        flash("This email is already registered!")

    finally:
        conn.close()

    return redirect(url_for("dashboard"))

# CHANGE PASSWORD
@app.route("/change-password", methods=["POST"])
def change_password():

    if "user_id" not in session:
        return redirect(url_for("login"))

    current_password = request.form.get("current_password", "")
    new_password = request.form.get("new_password", "")
    confirm_password = request.form.get("confirm_password", "")

    if not current_password or not new_password or not confirm_password:
        flash("Please fill in all password fields!")
        return redirect(url_for("dashboard"))

    if len(new_password) < 8:
        flash("New password must contain at least 8 characters!")
        return redirect(url_for("dashboard"))

    if new_password != confirm_password:
        flash("New passwords do not match!")
        return redirect(url_for("dashboard"))

    conn = get_db_connection()

    user = conn.execute(
        "SELECT password FROM users WHERE id = ?",
        (session["user_id"],)
    ).fetchone()

    if user is None:
        conn.close()
        session.clear()
        return redirect(url_for("login"))

    if not check_password_hash(user["password"], current_password):

        conn.close()
        flash("Current password is incorrect!")
        return redirect(url_for("dashboard"))

    hashed_password = generate_password_hash(new_password)

    conn.execute(
        "UPDATE users SET password = ? WHERE id = ?",
        (hashed_password, session["user_id"])
    )

    conn.commit()
    conn.close()

    flash("Password changed successfully!")

    return redirect(url_for("dashboard"))

# ADD TASK
@app.route("/api/tasks", methods=["POST"])
def add_task():

    if "user_id" not in session:
        return jsonify({"error": "Please login first"}), 401

    data = request.get_json(silent=True) or {}
    task = data.get("task", "").strip()

    if not task:
        return jsonify({"error": "Task cannot be empty"}), 400

    if len(task) > 100:
        return jsonify({"error": "Task must be 100 characters or less"}), 400

    conn = get_db_connection()

    cursor = conn.execute(
        "INSERT INTO tasks (user_id, task) VALUES (?, ?)",
        (session["user_id"], task)
    )

    conn.commit()

    task_id = cursor.lastrowid

    conn.close()

    return jsonify({
        "message": "Task added successfully",
        "id": task_id,
        "task": task,
        "completed": False
    }), 201


# GET TASKS
@app.route("/api/tasks", methods=["GET"])
def load_tasks():

    if "user_id" not in session:
        return jsonify({"error": "Please login first"}), 401

    tasks = get_tasks(session["user_id"])

    result = []

    for task in tasks:
        result.append({
            "id": task["id"],
            "task": task["task"],
            "completed": bool(task["completed"])
        })

    return jsonify(result)


# UPDATE TASK STATUS
@app.route("/api/tasks/<int:task_id>", methods=["PATCH"])
def update_task(task_id):

    if "user_id" not in session:
        return jsonify({"error": "Please login first"}), 401

    data = request.get_json(silent=True) or {}

    if not isinstance(data.get("completed"), bool):
        return jsonify({"error": "Invalid task status"}), 400

    completed = int(data["completed"])

    conn = get_db_connection()

    cursor = conn.execute(
        """
        UPDATE tasks
        SET completed = ?
        WHERE id = ? AND user_id = ?
        """,
        (completed, task_id, session["user_id"])
    )

    conn.commit()
    updated = cursor.rowcount

    conn.close()

    if updated == 0:
        return jsonify({"error": "Task not found"}), 404

    return jsonify({"message": "Task updated successfully"})


# DELETE ONE TASK
@app.route("/api/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):

    if "user_id" not in session:
        return jsonify({"error": "Please login first"}), 401

    conn = get_db_connection()

    cursor = conn.execute(
        "DELETE FROM tasks WHERE id = ? AND user_id = ?",
        (task_id, session["user_id"])
    )

    conn.commit()
    deleted = cursor.rowcount

    conn.close()

    if deleted == 0:
        return jsonify({"error": "Task not found"}), 404

    return jsonify({"message": "Task deleted successfully"})


# CLEAR COMPLETED TASKS
@app.route("/api/tasks/clear-completed", methods=["DELETE"])
def clear_completed():

    if "user_id" not in session:
        return jsonify({"error": "Please login first"}), 401

    conn = get_db_connection()

    conn.execute(
        "DELETE FROM tasks WHERE user_id = ? AND completed = 1",
        (session["user_id"],)
    )

    conn.commit()
    conn.close()

    return jsonify({"message": "Completed tasks cleared"})


# LOGOUT
@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("home"))


# START APPLICATION
if __name__ == "__main__":

    create_table()

    app.run(debug=True)


