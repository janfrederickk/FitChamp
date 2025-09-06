import os
import datetime
from fit_tool.fit_file import FitFile
from fit_tool.profile.messages import FileIdMessage, WorkoutMessage, WorkoutStepMessage
from fit_tool.profile.profile_type import Sport, Intensity, WorkoutStepDuration, WorkoutStepTarget, Manufacturer, FileType
from garminconnect import Garmin

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

# Add FileIdMessage
file_id_message = FileIdMessage()
file_id_message.type = FileType.WORKOUT
file_id_message.manufacturer = Manufacturer.GARMIN
file_id_message.product = 0
file_id_message.time_created = round(start_time.timestamp() * 1000)
file_id_message.serial_number = 12345678
fit_file.add_message(file_id_message)

# Add WorkoutMessage
workout_message = WorkoutMessage()
workout_message.workout_name = 'MMA Training'
workout_message.sport = Sport.MIXED_MARTIAL_ARTS
workout_message.num_valid_steps = 3
fit_file.add_message(workout_message)

# Add WorkoutStepMessages
steps = [
    ('Warm-up', Intensity.WARMUP, WorkoutStepDuration.TIME, 900, WorkoutStepTarget.HEART_RATE, 140),
    ('Training', Intensity.ACTIVE, WorkoutStepDuration.TIME, 3900, WorkoutStepTarget.HEART_RATE, 160),
    ('Cool-down', Intensity.COOLDOWN, WorkoutStepDuration.TIME, 600, WorkoutStepTarget.HEART_RATE, 140)
]

for step_name, intensity, duration_type, duration_time, target_type, target_value in steps:
    step = WorkoutStepMessage()
    step.workout_step_name = step_name
    step.intensity = intensity
    step.duration_type = duration_type
    step.duration_time = duration_time
    step.target_type = target_type
    step.target_value = target_value
    fit_file.add_message(step)

# Save FIT file
fit_file_path = 'mma_training_activity.fit'
fit_file.to_file(fit_file_path)
print(f"✅ Activity FIT file created: {fit_file_path}")

# Upload to Garmin Connect
garmin_user = os.getenv("GARMIN_USER")
garmin_pass = os.getenv("GARMIN_PASS")

if not garmin_user or not garmin_pass:
    raise ValueError("GARMIN_USER and GARMIN_PASS environment variables must be set.")

try:
    client = Garmin(garmin_user, garmin_pass)
    client.login()
    with open(fit_file_path, 'rb') as f:
        client.upload_activity(f)
    print("✅ Activity uploaded to Garmin Connect!")
except Exception as e:
    print(f"Error uploading activity: {e}")
