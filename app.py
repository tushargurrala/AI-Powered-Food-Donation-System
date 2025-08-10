from flask import Flask, request, jsonify, session, send_from_directory
from flask_cors import CORS
from datetime import datetime, timedelta
import joblib
import numpy as np
from werkzeug.security import generate_password_hash, check_password_hash
import os

# Configure Flask app
app = Flask(__name__, static_folder="../frontend", static_url_path="/")
CORS(app)
app.secret_key = "supersecret"  # Required for session handling

# Load ML model
model = joblib.load('ML/food_donation_predictor.pkl')

# In-memory stores
donations_list = []
users = []  # Format: {"username": "abc", "password": "<hashed>"}

# NGO list
ngos = [
    {"name": "Feeding India", "food_needed": "Rice", "max_qty": 10},
    {"name": "Robin Hood Army", "food_needed": "Vegetables", "max_qty": 15},
    {"name": "AnyHelp", "food_needed": "Any", "max_qty": 20}
]

# ========= FRONTEND ROUTES =========
@app.route('/')
def serve_index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/my_donations')
def serve_my_donations():
    return send_from_directory(app.static_folder, 'my_donations.html')

@app.route('/ngo_dashboard')
def serve_ngo_dashboard():
    return send_from_directory(app.static_folder, 'ngo_dashboard.html')

@app.route('/<path:filename>')
def serve_static_files(filename):
    return send_from_directory(app.static_folder, filename)

# ========= AUTHENTICATION =========
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    for user in users:
        if user["username"] == username:
            return jsonify({"error": "User already exists"}), 409

    hashed_pw = generate_password_hash(password)
    users.append({"username": username, "password": hashed_pw})

    return jsonify({"message": "Registration successful"})

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    for user in users:
        if user["username"] == username and check_password_hash(user["password"], password):
            session["user"] = username
            return jsonify({"message": "Login successful", "user": username})

    return jsonify({"error": "Invalid credentials"}), 401

@app.route('/logout', methods=['GET'])
def logout():
    session.pop("user", None)
    return jsonify({"message": "Logged out"})

# ========= ML Prediction =========
@app.route('/predict', methods=['POST'])
def predict():
    data = request.get_json()
    features = np.array([
        data['time_of_day'],
        data['day_of_week']
    ]).reshape(1, -1)

    prediction = model.predict(features)[0]
    return jsonify({'predicted_donation_kg': float(prediction)})

# ========= Submit Donation =========
@app.route('/submit_donation', methods=['POST'])
def submit_donation():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    food_type = data.get('food_type')
    quantity = float(data.get('quantity'))
    expiry_hours = int(data.get('expiry'))

    # ✅ Convert expiry hours into a proper ISO timestamp
    expiry_time = datetime.utcnow() + timedelta(hours=expiry_hours)

    best_match = None
    best_score = -1

    for ngo in ngos:
        score = 0
        if ngo["food_needed"].lower() == food_type.lower():
            score += 2
        elif ngo["food_needed"].lower() == "any":
            score += 1

        if quantity <= ngo["max_qty"]:
            score += 1
        if expiry_hours <= 12:  # fresh food bonus
            score += 1

        if score > best_score:
            best_score = score
            best_match = ngo["name"]

    donation_entry = {
        "food_type": food_type,
        "quantity": quantity,
        "expiry": expiry_time.isoformat(),  # ✅ ISO 8601 timestamp
        "matched_ngo": best_match if best_match else "No Match",
        "email": session.get("user"),
        "date": datetime.utcnow().isoformat()
    }
    donations_list.append(donation_entry)

    message = f"Donation submitted and matched with NGO: {best_match}" if best_match else "Donation submitted but no suitable NGO match found."
    return jsonify({'message': message, 'donation': donation_entry})

# ========= View Donations =========
@app.route('/donations', methods=['GET'])
def get_donations():
    return jsonify(donations_list[::-1])  # Return latest first

if __name__ == '__main__':
    app.run(debug=True)
