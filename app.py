import os
import requests
import smtplib
from email.message import EmailMessage
from flask import Flask, request, send_from_directory, jsonify
from dotenv import load_dotenv

load_dotenv("key.env")
app = Flask(__name__, static_folder="static")

# --- Config ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
FROM_EMAIL = os.getenv("FROM_EMAIL", "no-reply@example.com")

# --- Helper: AI summarizer ---
def summarize_with_groq(transcript, prompt):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    body = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant that summarizes text."},
            {"role": "user", "content": f"Transcript: {transcript}\n\nInstruction: {prompt}"}
        ],
        "temperature": 0.3,
    }

    print("📩 Sending to Groq:", body)   # ✅ debugging inside function

    resp = requests.post(url, headers=headers, json=body)
    print("🌐 Response:", resp.status_code, resp.text)  # ✅ debugging inside function

    if resp.status_code == 200:
        return resp.json()["choices"][0]["message"]["content"]
    else:
        return f"Error from Groq API: {resp.text}"

# --- Routes ---
@app.route("/summarize", methods=["POST"])
def summarize():
    try:
        prompt = request.form.get("prompt") or request.json.get("prompt")
        transcript = ""

        # If file uploaded
        if "file" in request.files:
            file = request.files["file"]
            transcript = file.read().decode("utf-8")  
        else:
            transcript = request.form.get("transcript") or request.json.get("transcript")

        if not transcript or len(transcript.strip()) < 5:
            return jsonify({"error": "Transcript too short"}), 400

        summary = summarize_with_groq(transcript, prompt or "Summarize key points and action items.")
        return jsonify({"summary": summary})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/send-email', methods=['POST'])
def send_email():
    try:
        data = request.json
        recipient = data.get("recipient")
        subject = data.get("subject")
        content = data.get("content")

        sender = os.getenv("SMTP_USER")
        password = os.getenv("SMTP_PASS")

        if not sender or not password:
            return jsonify({"error": "Missing SMTP_USER or SMTP_PASS in env"}), 500

        import smtplib
        from email.mime.text import MIMEText

        msg = MIMEText(content)
        msg["From"] = sender
        msg["To"] = recipient
        msg["Subject"] = subject

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, password)
            server.sendmail(sender, [recipient], msg.as_string())

        return jsonify({"success": True, "message": "Email sent successfully!"})

    except Exception as e:
        print("❌ Email error:", e)   # <-- log to console
        return jsonify({"error": str(e)}), 500

@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")

# --- Run ---
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
