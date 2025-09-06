import os
import datetime
import random
from garminconnect import (
    Garmin,
    GarminConnectConnectionError,
    GarminConnectAuthenticationError,
    GarminConnectTooManyRequestsError
)
from garmin_fit_sdk import FitFile, FitSessionMessage, FitRecordMessage

# Get Garmin credentials from environment variables
EMAIL = os.getenv("GARMIN_USER")
PASSWORD = os.getenv("GARMIN_PASS")

if not EMAIL or not PASSWORD:
    raise ValueError("GARMIN_USER and GARMIN_PASS environment variables must be set.")

# Activity parameters
WARMUP_DURATION = 15 * 60  # 15 minutes in seconds
TRAINING_DURATION = 65 * 60  # 65 minutes in seconds
COOLDOWN_DURATION = 10 * 60  # 10 minutes in seconds
TOTAL_DURATION = WARMUP_DURATION + TRAINING_DURATION + COOLDOWN_DURATION

# Calculate start time (90 minutes ago)
start_time = datetime.datetime.now() - datetime.timedelta(minutes=90)
start_time = start_time.replace(microsecond=0)

# Initialize FIT file
fit_file = FitFile()

# Add session message
fit_file.add_message(FitSessionMessage(
    sport='mixed_martial_arts',
    start_time=start_time,
    total_elapsed_time=TOTAL_DURATION
))

# Add heart rate records
time_cursor = start_time
for i in range(TOTAL_DURATION):
    if i < WARMUP_DURATION:
        hr = 100 + (140 - 100) * (i / WARMUP_DURATION)
    elif i < WARMUP_DURATION + TRAINING_DURATION:
        hr = random.randint(150, 170)
    else:
        hr = 170 - (170 - 140) * ((i - WARMUP_DURATION - TRAINING_DURATION) / COOLDOWN_DURATION)
    fit_file.add_message(FitRecordMessage(timestamp=time_cursor, heart_rate=int(hr)))
    time_cursor += datetime.timedelta(seconds=1)

# Save FIT file
fit_file_path = 'mma_training_activity.fit'
fit_file.to_file(fit_file_path)
print(f"✅ Activity FIT file created: {fit_file_path}")

# Upload to Garmin Connect
try:
    client = Garmin(EMAIL, PASSWORD)
    client.login()
    with open(fit_file_path, 'rb') as f:
        client.upload_activity(f)
    print("✅ Activity uploaded to Garmin Connect!")
except (GarminConnectAuthenticationError, GarminConnectConnectionError) as e:
    print(f"Error uploading activity: {e}")
except GarminConnectTooManyRequestsError:
    print("Too many requests. Please try again later.")
