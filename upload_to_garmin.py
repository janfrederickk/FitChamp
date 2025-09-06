import os
from garminconnect import Garmin

fit_file_path = "mma_training_activity.fit"

# Read Garmin credentials from environment variables
email = os.getenv("GARMIN_USER")
password = os.getenv("GARMIN_PASS")

if not email or not password:
    raise ValueError("GARMIN_USER and GARMIN_PASS must be set")

# Login and upload
client = Garmin(email, password)
client.login()

with open(fit_file_path, "rb") as f:
    client.upload_activity(f)

print(f"✅ Activity uploaded: {fit_file_path}")
