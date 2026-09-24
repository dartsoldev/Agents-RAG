<!-- Purpose: give the owner a practical Roman Urdu setup and demo walkthrough. -->
# Project kaise chalana hai

## Pehli dafa

PowerShell khol kar:

```powershell
cd 'D:\Agents-Arav Law Firm'
.\scripts\setup.ps1
.\scripts\start.ps1
```

Agar Windows script policy rokay, isi session ke liye command use kar sakte hain:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\start.ps1
```

Browser mein `http://127.0.0.1:8000` kholain. `localhost` ke bajaye yehi exact address use karein, kyun ke allowed origin `.env` mein isi address par set hai.

- Email: `admin@arav.local`
- Password: `ChangeMe-Demo-2026!`

Ye sirf local demo login hai. Real environment mein use na karein.

## Roz chalana

Sirf `.\scripts\start.ps1` chalana hai. PowerShell khula rakhein. Band karne ke liye Ctrl+C. Cases database mein save rahenge.

## Demo ka practical flow

1. Overview par 4 fictional cases nazar aayenge. John Smith kholain.
2. Documents mein medical record, insurance aur bills indexed milenge. Seed workflow ko kuch seconds dein.
3. Research mein “What injuries are documented?” poochain; source button se original evidence dekhein. API key ke baghair ye exact excerpts hain, AI-generated legal answer nahi.
4. Tasks mein missing records aur treatment/adjuster gaps dekhein. Checkbox se task complete kar sakte hain.
5. Overview mein medical aur insurance details edit karein. Tracking save par monitor job queue hota hai.
6. “Prepare demand packet” click karein, phir Activity mein completion dekhein.
7. Reviews mein draft edit, approve ya reject karein. Approved client email ko demo mein simulate kar sakte hain.
8. John ka treatment `complete` mark karein; ready medical, bills aur insurance records hon to stage `demand` ho sakta hai.
9. Demand packet approve kar ke `negotiation`, phir settlement amount ke saath `settled`, phir `closed` karein. Har stage par decision note required hai.
10. New case se apna fictional test case create karein. Duplicate email + accident date reject hogi.

## Keys kahan dalni hain

Root folder ki `.env` file mein. `.env.example` sirf reference template hai. Frontend mein koi key nahi dalni. OpenAI ke liye `OPENAI_API_KEY`; email ke liye `SMTP_*`; existing Filevine project link ke liye `FILEVINE_*`. Full detail `docs/INTEGRATIONS.md` mein hai.

`.env` edit karne ke baad Ctrl+C se server rok kar start karein. Existing staff ka password `.env` badalne se change nahi hota; password sirf initial bootstrap par apply hota hai. Reset ke liye:

```powershell
.\.venv\Scripts\python.exe -m scripts.manage_user reset-password admin@arav.local
```

Password terminal mein hidden prompt par enter hoga.

## Real cases ki taraf jana

Demo database mein real records mix na karein. Server stop karein; `.env` mein naya database/storage path, `DEMO_MODE=false`, `SEED_DEMO=false`, naya long admin password aur required provider keys set karein. PostgreSQL Docker configuration aur deployment limits README mein hain. Production hosting ke liye HTTPS, secure cookies, backups aur access configuration zaroori hain.

Local intake-to-closure flow implemented hai. External Filevine auto-sync, live case-law search, incoming phone/SMS, client portal aur OCR is version mein complete nahi hain; sirf keys dalne se ye extra features activate nahi honge. Integrations guide is difference ko clearly explain karti hai.
