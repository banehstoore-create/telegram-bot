from flask import Flask
from threading import Thread

# اول این خط باید باشد
app = Flask('')

@app.route('/')
def home():
    return "OK"

def run():
    # پورت Render معمولاً 80 یا 10000 است اما 8080 هم جواب می‌دهد
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()
