<<<<<<< HEAD
﻿// See https://aka.ms/new-console-template for more information
Console.WriteLine("Hello, World!");
=======
﻿using System;
using System.Diagnostics;
using Dynastream.Fit;

namespace MmaActivityGenerator
{
    class Program
    {
        static void Main(string[] args)
        {
            string fitFile = "mma_training_activity.fit";

            // Generate FIT
            GenerateFit(fitFile);

            Console.WriteLine("Uploading to Garmin Connect via Python...");

            // Call Python script
            var psi = new ProcessStartInfo
            {
                FileName = "python",
                Arguments = "upload_to_garmin.py",
                UseShellExecute = false,
                RedirectStandardOutput = true,
                RedirectStandardError = true
            };

            var process = Process.Start(psi);
            process.WaitForExit();

            Console.WriteLine(process.StandardOutput.ReadToEnd());
            var err = process.StandardError.ReadToEnd();
            if (!string.IsNullOrEmpty(err)) Console.WriteLine("Error: " + err);
        }

        static void GenerateFit(string fitFile)
        {
            DateTime startTime = DateTime.UtcNow.AddMinutes(-90);
            int warmup = 15 * 60;
            int training = 65 * 60;
            int cooldown = 10 * 60;
            int total = warmup + training + cooldown;

            using (Encode encoder = new Encode())
            {
                encoder.Open(fitFile);

                // File ID
                FileIdMesg fileId = new FileIdMesg();
                fileId.SetManufacturer((ushort)Manufacturer.Development);
                fileId.SetType(File.Activity);
                fileId.SetTimeCreated(DateTimeToFitTime(startTime));
                encoder.Write(fileId);

                // Session
                SessionMesg session = new SessionMesg();
                session.SetStartTime(DateTimeToFitTime(startTime));
                session.SetSport(Sport.MixedMartialArts);
                session.SetTotalElapsedTime(total);
                encoder.Write(session);

                // Records
                DateTime cursor = startTime;
                Random rand = new Random();
                for (int i = 0; i < total; i++)
                {
                    RecordMesg record = new RecordMesg();
                    record.SetTimestamp(DateTimeToFitTime(cursor));

                    int hr = i < warmup
                        ? 100 + (int)((140 - 100) * ((double)i / warmup))
                        : i < warmup + training
                            ? rand.Next(150, 170)
                            : 170 - (int)((170 - 140) * ((double)(i - warmup - training) / cooldown));

                    record.SetHeartRate((byte)hr);
                    encoder.Write(record);
                    cursor = cursor.AddSeconds(1);
                }

                encoder.Close();
            }

            Console.WriteLine($"✅ FIT file created: {fitFile}");
        }

        static uint DateTimeToFitTime(DateTime dt)
        {
            DateTime fitEpoch = new DateTime(1989, 12, 31, 0, 0, 0, DateTimeKind.Utc);
            return (uint)(dt.ToUniversalTime() - fitEpoch).TotalSeconds;
        }
    }
}
>>>>>>> 86ebd4e (hybrid)
