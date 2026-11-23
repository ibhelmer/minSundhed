# minSundhed

Copyright 2026 Ib Helmer Nielsen. Apache License 2.0.

Lokalt Python-dashboard til søvn (REM, let, dyb og vågen), VO₂ max, puls, hvilepuls, observeret maksimalpuls, SpO₂, HRV og træningsbelastning. Streamlit og Plotly. CSV samt Apple Health XML/ZIP understøttes. Demodata er syntetiske.

## Installation
```sh
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m streamlit run app.py --server.address 127.0.0.1
```
Åbn http://localhost:8501.

## Data
CSV: én række pr. lokal kalenderdag, dato YYYY-MM-DD.
`date,sleep_hours,rem_hours,light_hours,deep_hours,awake_hours,vo2max,heart_rate,resting_hr,max_hr,spo2,hrv,training_minutes,rpe`.
HRV i ms (brug samme metode, eksempelvis SDNN); VO₂ max i ml/kg/min, puls i bpm, SpO₂ i procent. RPE er selvrapporteret intensitet 0–10; registrer 0 minutter på hviledage. Manglende værdier er tomme, ikke nul. Ved flere træningspas kan en varighedsvægtet RPE anvendes. Apple Health importerer én valgt kilde pr. måletype, tildeler søvn til slutdatoen, og summerer ikke overlappende søvnintervaller. Træningsvarighed importeres; RPE skal tilføjes manuelt via CSV-eksport. Maksimalpuls er højeste registrerede stikprøve, ikke fysiologisk HRmax.

## Analyse
Session-RPE-belastning = minutter × RPE. 7- og 28-dages glidende gennemsnit kræver komplette daglige data. Personlig reference er medianen af de foregående 28 kalenderdage (mindst 14 observationer). Restitution vises som afvigelser i søvn, HRV og hvilepuls, ikke en klinisk valideret score. Pearson-korrelationer mellem daglige værdier og næste dags målinger er eksplorative, kræver mindst 10 par og viser ikke kausalitet.

## Lokal AI
Installer Ollama separat, kør `ollama pull llama3.2` og start Ollama. Dashboardet kan på eksplicit anmodning sende aggregeret statistik til den lokale Ollama API på 127.0.0.1:11434. Ingen cloud-API anvendes. AI-output kan være forkert og er ikke medicinsk rådgivning. Uden Ollama virker alle øvrige funktioner.

## Privatliv
Repository er offentligt: upload aldrig egne sundhedsdata, eksportfiler eller credentials. Appen gemmer ikke importerede data permanent. Kør kun lokalt; netværksdeployment kræver autentifikation og TLS. Smartwatch-målinger og restitutionstrends er ikke diagnostiske. Ved bekymrende symptomer skal man søge sundhedsfaglig hjælp.

## Licens
Apache-2.0. Se LICENSE og NOTICE.

## Garmin Connect Personal API
Brug Python 3.12 eller nyere. Opret en Personal API Key under Profile & Account → Settings → Personal API Key på Garmin Connect Web. Vælg Garmin Connect som datakilde i appen, indtast nøglen i det maskerede felt, vælg 7, 14, 30 eller 90 dage og klik Hent aktuelle Garmin-data. Appen bruger Garmins officielle Python-klient til tokenudveksling og API-kald. Nøgle og målinger holdes i sessionshukommelsen; klientens midlertidige tokenfil slettes efter synkronisering. Hent igen for at opdatere; uret skal først synkronisere med Garmin Connect. Manglende eller ukendte felter vises som manglende data. Garmin HRV er nattens gennemsnit og må ikke blandes ukritisk med Apple SDNN. RPE og eksplicitte hviledage skal stadig registreres i CSV til belastningsberegning. Integrationens feltmapping er ikke verificeret mod en rigtig Garmin-konto. Se https://github.com/garmin/connect-personal-api-python og https://developer.garmin.com/gc-developer-program/personal/personal-api/.
