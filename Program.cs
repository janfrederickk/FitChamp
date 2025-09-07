// See https://aka.ms/new-console-template for more information

using Dynastream.Fit;

Console.WriteLine("Hello, World!");

CreateTimeBasedActivity();


static void CreateTimeBasedActivity()
{
    const string FileName = "Ringen_Training.fit";

    var messages = new List<Mesg>();

    // The starting timestamp for the activity
    var startTime = new Dynastream.Fit.DateTime(System.DateTime.UtcNow.AddMinutes(-90));
    var warmupDuration = 15 * 60;
    var trainingDuration = 65 * 60;
    var cooldownDuration = 10 * 60;

    // Timer Events are a BEST PRACTICE for FIT ACTIVITY files
    var eventMesgStart = new EventMesg();
    eventMesgStart.SetTimestamp(startTime);
    eventMesgStart.SetEvent(Event.Timer);
    eventMesgStart.SetEventType(EventType.Start);
    messages.Add(eventMesgStart);

    // Create the Developer Id message for the developer data fields.
    var developerIdMesg = new DeveloperDataIdMesg();
    // It is a BEST PRACTICE to reuse the same Guid for all FIT files created by your platform
    byte[] appId = new Guid("c8cc1e8b-e741-4829-be6d-4f6f8a044ebf").ToByteArray();
    for (int i = 0; i < appId.Length; i++)
    {
        developerIdMesg.SetApplicationId(i, appId[i]);
    }
    developerIdMesg.SetDeveloperDataIndex(0);
    developerIdMesg.SetApplicationVersion(110);
    messages.Add(developerIdMesg);

    FieldDescriptionMesg hrFieldDescMesg = new FieldDescriptionMesg();
    hrFieldDescMesg.SetDeveloperDataIndex(0);
    hrFieldDescMesg.SetFieldDefinitionNumber(1);
    hrFieldDescMesg.SetFitBaseTypeId(FitBaseType.Uint8);
    hrFieldDescMesg.SetFieldName(0, "Heart Rate");
    hrFieldDescMesg.SetUnits(0, "bpm");
    hrFieldDescMesg.SetNativeFieldNum(RecordMesg.FieldDefNum.HeartRate);
    hrFieldDescMesg.SetNativeMesgNum(MesgNum.Record);
    messages.Add(hrFieldDescMesg);

    // Every FIT ACTIVITY file MUST contain Record messages
    var timestamp = new Dynastream.Fit.DateTime(startTime);
    Random random = new Random();

    // Warmup phase: ramp from 120 to 140 bpm over 15 minutes
    for (int i = 0; i < warmupDuration; i++)
    {
        var recordMesg = new RecordMesg();
        recordMesg.SetTimestamp(timestamp);

        // Calculate heart rate ramp from 120 to 140 over warmup duration
        double progress = (double)i / warmupDuration;
        byte heartRate = (byte)(120 + (140 - 120) * progress);
        recordMesg.SetHeartRate(heartRate);

        // Write the Record message to the output stream
        messages.Add(recordMesg);

        // Increment the timestamp by one second
        timestamp.Add(1);
    }

    // Training phase: heart rate between 150-170 with gradual changes
    byte currentHR = 150; // Start at 150 bpm
    
    for (int i = 0; i < trainingDuration; i++)
    {
        var recordMesg = new RecordMesg();
        recordMesg.SetTimestamp(timestamp);

        // Gradually change heart rate by 1-2 bpm, staying within 150-170 range
        int change = random.Next(-2, 3); // -2, -1, 0, 1, 2
        currentHR = (byte)Math.Max(150, Math.Min(170, currentHR + change));
        
        recordMesg.SetHeartRate(currentHR);

        // Write the Record message to the output stream
        messages.Add(recordMesg);

        // Increment the timestamp by one second
        timestamp.Add(1);
    }

    // Cooldown phase: ramp from 140 to 120 bpm over 10 minutes
    for (int i = 0; i < cooldownDuration; i++)
    {
        var recordMesg = new RecordMesg();
        recordMesg.SetTimestamp(timestamp);

        // Calculate heart rate ramp from 140 to 120 over cooldown duration
        double progress = (double)i / cooldownDuration;
        byte heartRate = (byte)(140 - (140 - 120) * progress);
        recordMesg.SetHeartRate(heartRate);

        // Write the Record message to the output stream
        messages.Add(recordMesg);

        // Increment the timestamp by one second
        timestamp.Add(1);
    }

    // Timer Events are a BEST PRACTICE for FIT ACTIVITY files
    var eventMesgStop = new EventMesg();
    eventMesgStop.SetTimestamp(timestamp);
    eventMesgStop.SetEvent(Event.Timer);
    eventMesgStop.SetEventType(EventType.StopAll);
    messages.Add(eventMesgStop);

    // Calculate total duration (warmup + training + cooldown)
    var totalDuration = warmupDuration + trainingDuration + cooldownDuration;

    // Every FIT ACTIVITY file MUST contain at least one Lap message
    var lapMesg = new LapMesg();
    lapMesg.SetMessageIndex(0);
    lapMesg.SetTimestamp(timestamp);
    lapMesg.SetStartTime(startTime);
    lapMesg.SetTotalElapsedTime(totalDuration);
    lapMesg.SetTotalTimerTime(totalDuration);
    messages.Add(lapMesg);

    // Every FIT ACTIVITY file MUST contain at least one Session message
    var sessionMesg = new SessionMesg();
    sessionMesg.SetMessageIndex(0);
    sessionMesg.SetTimestamp(timestamp);
    sessionMesg.SetStartTime(startTime);
    sessionMesg.SetTotalElapsedTime(totalDuration);
    sessionMesg.SetTotalTimerTime(totalDuration);
    sessionMesg.SetSport(Sport.MixedMartialArts);
    sessionMesg.SetSubSport(SubSport.Hiit);
    sessionMesg.SetFirstLapIndex(0);
    sessionMesg.SetNumLaps(1);
    sessionMesg.SetTotalCalories((ushort?)random.Next(975, 1275));
    messages.Add(sessionMesg);

    // Every FIT ACTIVITY file MUST contain EXACTLY one Activity message
    var activityMesg = new ActivityMesg();
    activityMesg.SetTimestamp(timestamp);
    activityMesg.SetNumSessions(1);
    var timezoneOffset = (int)TimeZoneInfo.Local.BaseUtcOffset.TotalSeconds;
    activityMesg.SetLocalTimestamp((uint)((int)timestamp.GetTimeStamp() + timezoneOffset));
    activityMesg.SetTotalTimerTime(totalDuration);
    messages.Add(activityMesg);

    CreateActivityFile(messages, FileName, startTime);
}


static void CreateActivityFile(List<Mesg> messages, String filename, Dynastream.Fit.DateTime startTime)
{
    // The combination of file type, manufacturer id, product id, and serial number should be unique.
    // When available, a non-random serial number should be used.
    Dynastream.Fit.File fileType = Dynastream.Fit.File.Activity;
    ushort manufacturerId = Manufacturer.Development;
    ushort productId = 0;
    float softwareVersion = 1.0f;

    Random random = new Random();
    uint serialNumber = (uint)random.Next();

    // Every FIT file MUST contain a File ID message
    var fileIdMesg = new FileIdMesg();
    fileIdMesg.SetType(fileType);
    fileIdMesg.SetManufacturer(manufacturerId);
    fileIdMesg.SetProduct(productId);
    fileIdMesg.SetTimeCreated(startTime);
    fileIdMesg.SetSerialNumber(serialNumber);

    // A Device Info message is a BEST PRACTICE for FIT ACTIVITY files
    var deviceInfoMesg = new DeviceInfoMesg();
    deviceInfoMesg.SetDeviceIndex(DeviceIndex.Creator);
    deviceInfoMesg.SetManufacturer(Manufacturer.Development);
    deviceInfoMesg.SetProduct(productId);
    deviceInfoMesg.SetProductName("FIT Cookbook"); // Max 20 Chars
    deviceInfoMesg.SetSerialNumber(serialNumber);
    deviceInfoMesg.SetSoftwareVersion(softwareVersion);
    deviceInfoMesg.SetTimestamp(startTime);

    // Create the output stream, this can be any type of stream, including a file or memory stream. Must have read/write access
    FileStream fitDest = new FileStream(filename, FileMode.Create, FileAccess.ReadWrite, FileShare.Read);

    // Create a FIT Encode object
    Encode encoder = new Encode(ProtocolVersion.V20);

    // Write the FIT header to the output stream
    encoder.Open(fitDest);

    // Write the messages to the file, in the proper sequence
    encoder.Write(fileIdMesg);
    encoder.Write(deviceInfoMesg);

    foreach (Mesg message in messages)
    {
        encoder.Write(message);
    }

    // Update the data size in the header and calculate the CRC
    encoder.Close();

    // Close the output stream
    fitDest.Close();

    Console.WriteLine($"Encoded FIT file {fitDest.Name}");
}