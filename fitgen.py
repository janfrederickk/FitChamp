import random
import datetime
from fit_tool.fit_file_builder import FitFileBuilder
from fit_tool.profile.messages.file_id_message import FileIdMessage
from fit_tool.profile.messages.session_message import SessionMessage
from fit_tool.profile.messages.lap_message import LapMessage
from fit_tool.profile.messages.record_message import RecordMessage
from fit_tool.profile.profile_type import Sport, SubSport, Manufacturer, FileType

def generate_fit(filename="ringen_training.fit",
                 warmup_dur=15, warmup_hr=140,
                 training_dur=65, training_min_hr=150, training_max_hr=170,
                 cooldown_dur=10, cooldown_hr=140):

    warmup_dur *= 60
    training_dur *= 60
    cooldown_dur *= 60
    total_duration = warmup_dur + training_dur + cooldown_dur
    start_time = datetime.datetime.now().replace(microsecond=0)

    builder = FitFileBuilder(auto_define=True)

    file_id = FileIdMessage()
    file_id.type = FileType.ACTIVITY
    file_id.manufacturer = Manufacturer.GARMIN
    file_id.product = 1
    file_id.time_created = start_time
    file_id.serial_number = int(start_time.timestamp())
    builder.add(file_id)

    lap = LapMessage()
    lap.start_time = start_time
    lap.timestamp = start_time
    lap.sport = Sport.MIXED_MARTIAL_ARTS
    lap.sub_sport = SubSport.GENERIC
    builder.add(lap)

    session = SessionMessage()
    session.start_time = start_time
    session.timestamp = start_time
    session.total_elapsed_time = total_duration
    session.total_timer_time = total_duration
    session.sport = Sport.MIXED_MARTIAL_ARTS
    session.sub_sport = SubSport.GENERIC
    session.sport_name = "Ringen Training"
    builder.add(session)

    time_cursor = start_time

    def add_record(ts, hr):
        rec = RecordMessage()
        rec.timestamp = ts
        rec.heart_rate = int(hr)
        builder.add(rec)

    for i in range(warmup_dur):
        hr = 100 + (warmup_hr - 100) * (i / warmup_dur)
        add_record(time_cursor, hr)
        time_cursor += datetime.timedelta(seconds=1)

    for i in range(training_dur):
        hr = random.randint(training_min_hr, training_max_hr)
        add_record(time_cursor, hr)
        time_cursor += datetime.timedelta(seconds=1)

    for i in range(cooldown_dur):
        hr = training_max_hr - (training_max_hr - cooldown_hr) * (i / cooldown_dur)
        add_record(time_cursor, hr)
        time_cursor += datetime.timedelta(seconds=1)

    fit_file = builder.build()
    with open(filename, "wb") as f:
        fit_file.write(f)

    return filename
