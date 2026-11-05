<<<<<<< HEAD
# DeepShield

=======
# Deepshield-AI-Forgery-Detector-FYP0
DeepShield
>>>>>>> 762d8f2f77721741b97c9bfdfd7c9fcf88f525fc
DeepShield is a full-stack forensic media analysis system for detecting manipulated and AI-generated images/videos. It combines a FastAPI/PyTorch inference backend, a Flutter user application, a React investigator/admin dashboard, Supabase authentication/storage/database services, PDF forensic reports, and a local EVM-compatible blockchain notary for report verification.

The project was built as an FYP system around a practical workflow:

<<<<<<< HEAD
1. A user signs up or logs in.
2. The user uploads an image or video for analysis.
3. The backend classifies the media as `Authentic`, `Manipulated`, `Inconclusive`, or `AI-Generated`.
4. If relevant, the backend generates a Grad-CAM style heatmap.
5. The analysis is saved to Supabase, duplicate files are detected by SHA-256 hash, and a PDF report is generated.
6. The report hash is anchored to a local Hardhat blockchain.
7. Admin/investigator users can review analyses, audit logs, blockchain status, users, notes, and system settings from the dashboard.

## Repository Structure

```text
=======
A user signs up or logs in.
The user uploads an image or video for analysis.
The backend classifies the media as Authentic, Manipulated, Inconclusive, or AI-Generated.
If relevant, the backend generates a Grad-CAM style heatmap.
The analysis is saved to Supabase, duplicate files are detected by SHA-256 hash, and a PDF report is generated.
The report hash is anchored to a local Hardhat blockchain.
Admin/investigator users can review analyses, audit logs, blockchain status, users, notes, and system settings from the dashboard.
Repository Structure
>>>>>>> 762d8f2f77721741b97c9bfdfd7c9fcf88f525fc
.
|-- backend/                 # FastAPI API, PyTorch models, reports, Supabase, blockchain
|-- deepshield-frontend/     # Flutter mobile/desktop/web user application
`-- deepshield-admin/        # React + Vite investigator/admin dashboard
<<<<<<< HEAD
```

## Main Features

- Deepfake image/video analysis through a UCF primary model.
- Xception support model for frame-level video evidence.
- AI-generated image detection with optional trained classifier and fallback heuristics.
- Four-band forensic output: real/authentic, unsure, likely fake, strong fake.
- Grad-CAM/heatmap generation for significant manipulation evidence.
- Supabase email/password authentication.
- Authenticated user analysis history.
- SHA-256 deduplication to avoid repeated expensive inference on the same file.
- Supabase Storage uploads for heatmaps and PDF reports.
- PDF forensic report generation.
- QR/public verification endpoint for report validation.
- Local Hardhat blockchain anchoring for report hashes.
- Admin dashboard with metrics, analysis review, notes, users, settings, audit logs, and blockchain status.

## Tech Stack

### Backend

- Python
- FastAPI
- Uvicorn
- PyTorch / TorchVision
- OpenCV
- Pillow / NumPy
- Supabase Python client
- WeasyPrint
- Web3.py
- Hardhat local blockchain

### User App

- Flutter
- Dart
- `http`
- `flutter_dotenv`
- `file_picker`
- `flutter_secure_storage`
- `url_launcher`

### Admin Dashboard

- React
- TypeScript
- Vite
- Tailwind CSS
- Recharts
- Lucide React
- React Router

## Prerequisites

Install these before running the full system:

- Python 3.10 or newer
- Node.js and npm
- Flutter SDK compatible with Dart `^3.9.2`
- Git
- A Supabase project
- Model checkpoint files for the backend

For PDF report generation, WeasyPrint also needs system libraries:

- Ubuntu/Debian: `sudo apt-get install libpango-1.0-0 libpangoft2-1.0-0 libcairo2`
- macOS: `brew install pango cairo`
- Windows: install the GTK3 runtime required by WeasyPrint

## Backend Setup

Open a terminal at the repository root.

```powershell
=======
Main Features
Deepfake image/video analysis through a UCF primary model.
Xception support model for frame-level video evidence.
AI-generated image detection with optional trained classifier and fallback heuristics.
Four-band forensic output: real/authentic, unsure, likely fake, strong fake.
Grad-CAM/heatmap generation for significant manipulation evidence.
Supabase email/password authentication.
Authenticated user analysis history.
SHA-256 deduplication to avoid repeated expensive inference on the same file.
Supabase Storage uploads for heatmaps and PDF reports.
PDF forensic report generation.
QR/public verification endpoint for report validation.
Local Hardhat blockchain anchoring for report hashes.
Admin dashboard with metrics, analysis review, notes, users, settings, audit logs, and blockchain status.
Tech Stack
Backend
Python
FastAPI
Uvicorn
PyTorch / TorchVision
OpenCV
Pillow / NumPy
Supabase Python client
WeasyPrint
Web3.py
Hardhat local blockchain
User App
Flutter
Dart
http
flutter_dotenv
file_picker
flutter_secure_storage
url_launcher
Admin Dashboard
React
TypeScript
Vite
Tailwind CSS
Recharts
Lucide React
React Router
Prerequisites
Install these before running the full system:

Python 3.10 or newer
Node.js and npm
Flutter SDK compatible with Dart ^3.9.2
Git
A Supabase project
Model checkpoint files for the backend
For PDF report generation, WeasyPrint also needs system libraries:

Ubuntu/Debian: sudo apt-get install libpango-1.0-0 libpangoft2-1.0-0 libcairo2
macOS: brew install pango cairo
Windows: install the GTK3 runtime required by WeasyPrint
Backend Setup
Open a terminal at the repository root.

>>>>>>> 762d8f2f77721741b97c9bfdfd7c9fcf88f525fc
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
<<<<<<< HEAD
```

Create the model weights directory:

```powershell
mkdir weights
```

Place the trained model files here:

```text
backend/weights/ucf_best.pth
backend/weights/xception_best.pth
backend/weights/ai_classifier.pth   # optional
```

The UCF and Xception files are required for normal inference startup. The AI classifier is optional; if it is missing, the backend logs a warning and uses fallback AI-detection logic.

### Backend Environment Variables

Create `backend/.env`:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-supabase-anon-key
SUPABASE_SERVICE_KEY=your-supabase-service-role-key
```

`SUPABASE_ANON_KEY` is used for auth operations. `SUPABASE_SERVICE_KEY` is used by the backend to write analysis rows, upload report metadata, write admin audit logs, and manage related records.

### Run the Backend

From `backend/`:

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Production-style single-worker run:

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
```

=======
Create the model weights directory:

mkdir weights
Place the trained model files here:

backend/weights/ucf_best.pth
backend/weights/xception_best.pth
backend/weights/ai_classifier.pth   # optional
The UCF and Xception files are required for normal inference startup. The AI classifier is optional; if it is missing, the backend logs a warning and uses fallback AI-detection logic.

Backend Environment Variables
Create backend/.env:

SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-supabase-anon-key
SUPABASE_SERVICE_KEY=your-supabase-service-role-key
SUPABASE_ANON_KEY is used for auth operations. SUPABASE_SERVICE_KEY is used by the backend to write analysis rows, upload report metadata, write admin audit logs, and manage related records.

Run the Backend
From backend/:

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
Production-style single-worker run:

uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
>>>>>>> 762d8f2f77721741b97c9bfdfd7c9fcf88f525fc
Use one worker because the app loads PyTorch models at startup and also manages a local Hardhat process.

The backend will be available at:

<<<<<<< HEAD
- API root: `http://localhost:8000/`
- Swagger docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

## Blockchain Setup

The backend starts the local blockchain automatically at FastAPI startup through `backend/blockchain/node_manager.py`.

On first run it will:

1. Install Hardhat dependencies in `backend/blockchain/hardhat/` if `node_modules` is missing.
2. Compile `DeepShieldNotary.sol`.
3. Start a local Hardhat node on `http://127.0.0.1:8545`.
4. Deploy the notary smart contract.

You can also manage the Hardhat project manually:

```powershell
=======
API root: http://localhost:8000/
Swagger docs: http://localhost:8000/docs
Health check: http://localhost:8000/health
Blockchain Setup
The backend starts the local blockchain automatically at FastAPI startup through backend/blockchain/node_manager.py.

On first run it will:

Install Hardhat dependencies in backend/blockchain/hardhat/ if node_modules is missing.
Compile DeepShieldNotary.sol.
Start a local Hardhat node on http://127.0.0.1:8545.
Deploy the notary smart contract.
You can also manage the Hardhat project manually:

>>>>>>> 762d8f2f77721741b97c9bfdfd7c9fcf88f525fc
cd backend\blockchain\hardhat
npm install
npm run compile
npm run node
<<<<<<< HEAD
```

The local chain uses:

- RPC URL: `http://127.0.0.1:8545`
- Chain ID: `31337`
- Default Hardhat account/private key from the local development node

Blockchain failure does not stop media analysis. If the node cannot start or deploy, the backend continues and marks blockchain anchoring as failed or unavailable.

## Supabase Setup

DeepShield expects Supabase for:

- User authentication
- Analysis persistence
- Duplicate tracking
- Heatmap storage
- PDF report storage
- Admin profiles and role checks
- Admin audit logs
- Blockchain anchor metadata

Expected storage buckets:

```text
heatmaps
reports
```

Expected tables used by the backend/admin dashboard:

```text
=======
The local chain uses:

RPC URL: http://127.0.0.1:8545
Chain ID: 31337
Default Hardhat account/private key from the local development node
Blockchain failure does not stop media analysis. If the node cannot start or deploy, the backend continues and marks blockchain anchoring as failed or unavailable.

Supabase Setup
DeepShield expects Supabase for:

User authentication
Analysis persistence
Duplicate tracking
Heatmap storage
PDF report storage
Admin profiles and role checks
Admin audit logs
Blockchain anchor metadata
Expected storage buckets:

heatmaps
reports
Expected tables used by the backend/admin dashboard:

>>>>>>> 762d8f2f77721741b97c9bfdfd7c9fcf88f525fc
analyses
dedup_references
pdf_reports
blockchain_anchors
admin_profiles
analysis_review_notes
admin_audit_logs
system_settings
<<<<<<< HEAD
```

At minimum, create an `admin_profiles` row for any user who should access the admin dashboard. The dashboard allows these roles:

```text
admin
investigator
viewer
```

The profile must have `status = active`.

## Backend API Summary

### Public / Core

- `GET /`  
  Returns service metadata.

- `GET /health`  
  Returns backend status and model readiness.

- `POST /analyze`  
  Accepts multipart form data with a `file` field. Supports images and videos. Authentication is optional; if a valid bearer token is supplied, the analysis is attached to that user.

- `GET /verify/{analysis_id}`  
  Public verification endpoint for PDF/QR report checks.

### Authentication

- `POST /auth/signup`
- `POST /auth/login`
- `POST /auth/logout`

### Authenticated User

- `GET /analyses/history`
- `GET /analyses/{analysis_id}`

### Admin

- `GET /admin/me`
- `GET /admin/metrics`
- `GET /admin/analyses`
- `GET /admin/analyses/{analysis_id}`
- `PATCH /admin/analyses/{analysis_id}/review-status`
- `POST /admin/analyses/{analysis_id}/notes`
- `GET /admin/users`
- `PATCH /admin/users/{user_id}`
- `GET /admin/settings`
- `PATCH /admin/settings/{key}`
- `GET /admin/audit-logs`
- `GET /admin/blockchain/status`

## Example Analysis Request

```powershell
curl -X POST "http://localhost:8000/analyze" `
  -F "file=@C:\path\to\sample.jpg"
```

With authentication:

```powershell
curl -X POST "http://localhost:8000/analyze" `
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" `
  -F "file=@C:\path\to\sample.mp4"
```

Typical response:

```json
=======
At minimum, create an admin_profiles row for any user who should access the admin dashboard. The dashboard allows these roles:

admin
investigator
viewer
The profile must have status = active.

Backend API Summary
Public / Core
GET /
Returns service metadata.

GET /health
Returns backend status and model readiness.

POST /analyze
Accepts multipart form data with a file field. Supports images and videos. Authentication is optional; if a valid bearer token is supplied, the analysis is attached to that user.

GET /verify/{analysis_id}
Public verification endpoint for PDF/QR report checks.

Authentication
POST /auth/signup
POST /auth/login
POST /auth/logout
Authenticated User
GET /analyses/history
GET /analyses/{analysis_id}
Admin
GET /admin/me
GET /admin/metrics
GET /admin/analyses
GET /admin/analyses/{analysis_id}
PATCH /admin/analyses/{analysis_id}/review-status
POST /admin/analyses/{analysis_id}/notes
GET /admin/users
PATCH /admin/users/{user_id}
GET /admin/settings
PATCH /admin/settings/{key}
GET /admin/audit-logs
GET /admin/blockchain/status
Example Analysis Request
curl -X POST "http://localhost:8000/analyze" `
  -F "file=@C:\path\to\sample.jpg"
With authentication:

curl -X POST "http://localhost:8000/analyze" `
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" `
  -F "file=@C:\path\to\sample.mp4"
Typical response:

>>>>>>> 762d8f2f77721741b97c9bfdfd7c9fcf88f525fc
{
  "prediction": "Manipulated",
  "confidence": 0.91,
  "band": "Strong Fake",
  "type": "image",
  "heatmap_url": "https://...",
  "thresholds": {
    "real": 0.35,
    "fake": 0.55
  },
  "details": {
    "model": "ucf",
    "ucf_prob": 0.91,
    "ai_prob": 0.12
  },
  "analysis_id": "uuid",
  "file_hash": "sha256",
  "report_url": null,
  "blockchain_status": "pending",
  "is_duplicate": false,
  "prior_analyses": []
}
<<<<<<< HEAD
```

PDF report generation and blockchain anchoring run as background work after the analysis response is returned. Poll `GET /analyses/{analysis_id}` from an authenticated client or use the admin dashboard to see updated report/blockchain fields.

## Flutter App Setup

Open a second terminal:

```powershell
cd deepshield-frontend
flutter pub get
```

Create `deepshield-frontend/.env`:

```env
=======
PDF report generation and blockchain anchoring run as background work after the analysis response is returned. Poll GET /analyses/{analysis_id} from an authenticated client or use the admin dashboard to see updated report/blockchain fields.

Flutter App Setup
Open a second terminal:

cd deepshield-frontend
flutter pub get
Create deepshield-frontend/.env:

>>>>>>> 762d8f2f77721741b97c9bfdfd7c9fcf88f525fc
DEEPSHIELD_API_URL=http://localhost:8000
API_BASE_URL=http://localhost:8000
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-supabase-anon-key
APP_ENV=development
<<<<<<< HEAD
```

Run the app:

```powershell
flutter run
```

Useful targets:

```powershell
flutter run -d chrome
flutter run -d windows
flutter run -d android
```

When running on the Android emulator, the app automatically rewrites `localhost` or `127.0.0.1` API URLs to `10.0.2.2`, which is the emulator address for the host machine.

## Admin Dashboard Setup

Open a third terminal:

```powershell
cd deepshield-admin
npm install
```

Create `deepshield-admin/.env`:

```env
VITE_API_URL=http://localhost:8000
```

Run the dashboard:

```powershell
npm run dev
```

Vite will print a local URL, usually:

```text
http://localhost:5173
```

Login with a Supabase user that also has an active row in `admin_profiles`.

## Development Workflow

Start the system in this order:

1. Start the backend:

   ```powershell
   cd backend
   .\.venv\Scripts\Activate.ps1
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. Start the Flutter app:

   ```powershell
   cd deepshield-frontend
   flutter run
   ```

3. Start the admin dashboard:

   ```powershell
   cd deepshield-admin
   npm run dev
   ```

## Testing and Checks

Backend smoke check:

```powershell
cd backend
python verify_startup.py
```

Backend test scripts present in the repository:

```powershell
python test_ai_diag.py
python test_fusion.py
python test_v21.py
```

Flutter checks:

```powershell
cd deepshield-frontend
flutter analyze
flutter test
```

Admin checks:

```powershell
cd deepshield-admin
npm run lint
npm run build
```

## Important Configuration Values

Backend thresholds are defined in `backend/config.py` and `backend/core/config.py`:

- `REAL_THRESHOLD = 0.35`
- `FAKE_THRESHOLD = 0.55`
- `AI_DETECTION_THRESHOLD = 0.55`
- `MAX_FILE_SIZE_MB = 50`

Default backend output directory:

```text
backend/outputs
```

Default backend weights directory:

```text
backend/weights
```

## Supported Upload Types

Images:

```text
jpg, jpeg, png, webp, bmp, tiff
```

Videos:

```text
mp4, mov, avi, mkv, webm, flv, mpg, mpeg
```

The Flutter client currently communicates the most common accepted formats to users: JPG, PNG, WEBP, MP4, MOV, and AVI.

## Troubleshooting

### Backend fails at startup because weights are missing

Create `backend/weights/` and add:

```text
ucf_best.pth
xception_best.pth
```

Add `ai_classifier.pth` only if you have the trained AI classifier.

### Supabase authentication fails

Check that `backend/.env` contains:

```env
SUPABASE_URL=...
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_KEY=...
```

Restart the backend after editing `.env`.

### Admin dashboard says admin access is required

The logged-in Supabase user must have a matching row in `admin_profiles`:

```text
id = Supabase user UUID
role = admin, investigator, or viewer
status = active
```

### Flutter cannot reach the backend

Confirm the backend is running on `http://localhost:8000`. For Android emulator runs, keep `DEEPSHIELD_API_URL=http://localhost:8000`; the app rewrites it to `10.0.2.2` automatically.

### Blockchain status is failed or attention

Install Node dependencies manually:

```powershell
cd backend\blockchain\hardhat
npm install
npm run compile
```

Then restart the backend. Make sure port `8545` is free.

### PDF generation fails on Windows

Install the GTK3 runtime required by WeasyPrint, then restart the backend.

## Notes for Deployment

- Replace `allow_origins=["*"]` in the backend CORS setup with your production frontend/admin domains.
- Do not expose `SUPABASE_SERVICE_KEY` to the Flutter or React clients.
- Run FastAPI behind a production server/reverse proxy.
- Use a production blockchain/RPC strategy if public verification is required outside the local development machine.
- Store model weights outside source control.
- Use private Supabase buckets or signed URLs if report/heatmap access needs stricter privacy.

## Project Status

=======
Run the app:

flutter run
Useful targets:

flutter run -d chrome
flutter run -d windows
flutter run -d android
When running on the Android emulator, the app automatically rewrites localhost or 127.0.0.1 API URLs to 10.0.2.2, which is the emulator address for the host machine.

Admin Dashboard Setup
Open a third terminal:

cd deepshield-admin
npm install
Create deepshield-admin/.env:

VITE_API_URL=http://localhost:8000
Run the dashboard:

npm run dev
Vite will print a local URL, usually:

http://localhost:5173
Login with a Supabase user that also has an active row in admin_profiles.

Development Workflow
Start the system in this order:

Start the backend:

cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
Start the Flutter app:

cd deepshield-frontend
flutter run
Start the admin dashboard:

cd deepshield-admin
npm run dev
Testing and Checks
Backend smoke check:

cd backend
python verify_startup.py
Backend test scripts present in the repository:

python test_ai_diag.py
python test_fusion.py
python test_v21.py
Flutter checks:

cd deepshield-frontend
flutter analyze
flutter test
Admin checks:

cd deepshield-admin
npm run lint
npm run build
Important Configuration Values
Backend thresholds are defined in backend/config.py and backend/core/config.py:

REAL_THRESHOLD = 0.35
FAKE_THRESHOLD = 0.55
AI_DETECTION_THRESHOLD = 0.55
MAX_FILE_SIZE_MB = 50
Default backend output directory:

backend/outputs
Default backend weights directory:

backend/weights
Supported Upload Types
Images:

jpg, jpeg, png, webp, bmp, tiff
Videos:

mp4, mov, avi, mkv, webm, flv, mpg, mpeg
The Flutter client currently communicates the most common accepted formats to users: JPG, PNG, WEBP, MP4, MOV, and AVI.

Troubleshooting
Backend fails at startup because weights are missing
Create backend/weights/ and add:

ucf_best.pth
xception_best.pth
Add ai_classifier.pth only if you have the trained AI classifier.

Supabase authentication fails
Check that backend/.env contains:

SUPABASE_URL=...
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_KEY=...
Restart the backend after editing .env.

Admin dashboard says admin access is required
The logged-in Supabase user must have a matching row in admin_profiles:

id = Supabase user UUID
role = admin, investigator, or viewer
status = active
Flutter cannot reach the backend
Confirm the backend is running on http://localhost:8000. For Android emulator runs, keep DEEPSHIELD_API_URL=http://localhost:8000; the app rewrites it to 10.0.2.2 automatically.

Blockchain status is failed or attention
Install Node dependencies manually:

cd backend\blockchain\hardhat
npm install
npm run compile
Then restart the backend. Make sure port 8545 is free.

PDF generation fails on Windows
Install the GTK3 runtime required by WeasyPrint, then restart the backend.

Notes for Deployment
Replace allow_origins=["*"] in the backend CORS setup with your production frontend/admin domains.
Do not expose SUPABASE_SERVICE_KEY to the Flutter or React clients.
Run FastAPI behind a production server/reverse proxy.
Use a production blockchain/RPC strategy if public verification is required outside the local development machine.
Store model weights outside source control.
Use private Supabase buckets or signed URLs if report/heatmap access needs stricter privacy.
Project Status
>>>>>>> 762d8f2f77721741b97c9bfdfd7c9fcf88f525fc
This repository contains a working FYP-style full-stack prototype with production-oriented components. The core analysis pipeline, user app, admin dashboard, Supabase persistence, PDF reports, and local blockchain anchoring are implemented, but deployment hardening, database migrations, model weight distribution, and production blockchain configuration should be finalized before public release.
