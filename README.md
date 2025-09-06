# Wrestling FIT File Generator & Garmin Upload

This repository generates a **synthetic FIT file** for your wrestling training and uploads it directly to **Garmin Connect**.  
The activity is logged as **Mixed Martial Arts** with the name **"Ringen Training"**.

Execution is manual via **GitHub Actions**, so no server or VM is required.

---

## Features

- Automatically generates a FIT file with:
  - 15 minutes Warm-up (max HR 140 bpm)  
  - 65 minutes Training (HR 150–170 bpm, random)  
  - 10 minutes Cool-down (HR down to 140 bpm)  
- Garmin Connect activity:
  - Name: `Ringen Training`  
  - Sport: `Mixed Martial Arts`  
- Secure upload via **GitHub Actions** using Secrets  
- Manual triggering via GitHub (`workflow_dispatch`)

---

## Setup

1. **Clone or create the repository**

```bash
git clone <repo-url>
cd ringen-fit-generator
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

2. **Optional: Install Python dependencies locally**

``` bash
python -m venv venv
source venv/bin/activate # Linux/macOS
venv\Scripts\activate # Windows
pip install -r requirements.txt
``` 


3. **Add GitHub Secrets**

- `GARMIN_USER` → your Garmin username  
- `GARMIN_PASS` → your Garmin password  

> Go to GitHub → Repository → Settings → Secrets → Actions → New repository secret

---

## Usage

### Manual via GitHub Actions

1. Go to **Actions → Garmin Ringen Upload**  
2. Click **Run workflow**  
3. The workflow generates the FIT file and uploads it automatically to Garmin Connect  

> You can also trigger the action using the **GitHub app on your iPhone**.

---

## FIT File Generation

The script `fitgen.py` generates the FIT file with second-by-second heart rate data:

- Warm-up: linear increase 100 → 140 bpm  
- Training: random values 150–170 bpm  
- Cool-down: linear decrease 170 → 140 bpm  

---

## Security

- No passwords in code – only via **GitHub Secrets**  
- Workflow runs on GitHub runners, no public VM required  

---

## Optional

- Workflow can be extended to:
  - Accept parameters for duration or HR zones via `workflow_dispatch` inputs  
  - Show progress/status messages in the workflow log
