"""Run once to save Gmail app passwords locally."""
import json
import getpass

p1 = getpass.getpass("App password for oluwadameelola@gmail.com: ")
p2 = getpass.getpass("App password for bamee221@gmail.com: ")

with open("saved_config.json", "w") as f:
    json.dump({"gmail_password": p1, "gmail_password_2": p2}, f)
print("Saved.")
