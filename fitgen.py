import random
import datetime
from fitparse import FitFile
from fitparse.records import Record

def generate_fit(filename="ringen_training.fit",
                 warmup_dur=15, warmup_hr=140,
                 training_dur=65, training_min_hr=150, training_max_hr=170,
                 cooldown_dur=10, cooldown_hr=140):

    # Convert minutes to seconds
    warmup_dur *= 60
    training_dur *= 60
    cooldown_dur *= 60

    # Start time 90 minutes in the past
    start_time = datetime.datetime.now() - datetime.timedelta(minutes=90)
    start_time = start_time.replace(microsecond=0)
    time_cursor = start_time

    # Create a new FIT file
    fitfile = FitFile()

    # Add activity metadata
    fitfile.add_file_id(type="activity", manufacturer="garmin", product=1, time_created=start_time)
    fitfile.add_session(
        start_time=start_time,
        sport="mixed_martial_arts",  # MMA
        sub_sport="generic",
        total_elapsed_time=warmup_dur + training_dur + cooldown_dur,
        total_timer_time=warmup_dur + training_dur + cooldown_dur
    )

    fitfile.add_lap(
        start_time=start_time,
        sport="mixed_martial_arts",
        sub_sport="generic",
        total_elapsed_time=warmup_dur + training_dur + cooldown_dur
    )

    # Helper to add HR record
    def add_hr_record(ts, hr):
        record = Record()
        record.timestamp = ts
        record.heart_rate = int(hr)
        fitfile.add_record(record)

    # Warm-up
    for i in range(warmup_dur):
        hr = 100 + (warmup_hr - 100) * (i / warmup_dur)
        add_hr_record(time_cursor, hr)
        time_cursor += datetime.timedelta(seconds=1)

    # Training
    for i in range(training_dur):
        hr = random.randint(training_min_hr, training_max_hr)
        add_hr_record(time_cursor, hr)
        time_cursor += datetime.timedelta(seconds=1)

    # Cool-down
    for i in range(cooldown_dur):
        hr = training_max_hr - (training_max_hr - cooldown_hr) * (i / cooldown_dur)
        add_hr_record(time_cursor, hr)
        time_cursor += datetime.timedelta(seconds=1)

    # Save the FIT file
    fitfile.save(filename)
    print(f"✅ FIT file '{filename}' generated successfully!")
    return filename
