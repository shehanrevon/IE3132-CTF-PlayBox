from flask import Flask, request, render_template_string
import subprocess
import os

app = Flask(__name__)
UPLOAD_FOLDER = "/tmp/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

INDEX_HTML = """
<h2>Silent Ledger — Internal File Converter</h2>
<form method="POST" action="/convert" enctype="multipart/form-data">
    <input type="file" name="file">
    <input type="submit" value="Convert">
</form>
"""

@app.route("/")
def index():
    return INDEX_HTML

@app.route("/convert", methods=["POST"])
def convert():
    f = request.files["file"]
    filepath = os.path.join(UPLOAD_FOLDER, f.filename)
    f.save(filepath)
    # VULNERABILITY: filename passed unsanitized into a shell command
    result = subprocess.run(f"file {filepath}", shell=True, capture_output=True, text=True)
    return f"<pre>{result.stdout}</pre>"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
