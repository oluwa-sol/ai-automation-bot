"""Run once to save your Gmail app password locally."""
import json
import getpass

password = getpass.getpass("Gmail app password: ")
with open("saved_config.json", "w") as f:
    json.dump({"gmail_password": password}, f)
print("Saved.")
