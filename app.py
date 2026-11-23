# Copyright 2026 Ib Helmer Nielsen
# SPDX-License-Identifier: Apache-2.0
import pandas as pd
import plotly.express as px
import requests
import streamlit as st
from health import demo, normalize, apple, analyze, correlations, FIELDS

st.set_page_config(page_title="minSundhed",page_icon="❤️",layout="wide")
st.title("minSundhed")
st.caption("Personligt sundheds- og træningsdashboard • ikke et medicinsk værktøj")
source=st.sidebar.radio("Datakilde",["Garmin Connect","Filimport","Demodata"],index=2)
upload=st.sidebar.file_uploader("Importer sundhedsdata",type=["csv","xml","zip"]) if source=="Filimport" else None
if source=="Garmin Connect":
    key=st.sidebar.text_input("Garmin Connect Personal API-nøgle",type="password",key="garmin_key")
    days=st.sidebar.selectbox("Synkroniseringsperiode (dage)",[7,14,30,90],index=1)
    if st.sidebar.button("Afbryd og ryd Garmin-data"):
        st.session_state.pop("garmin_data",None)
        st.session_state.pop("garmin_sync_time",None)
        st.session_state.pop("garmin_warnings",None)
        st.stop()
    if st.sidebar.button("Hent aktuelle Garmin-data",disabled=not key.strip()):
        from garmin_sync import sync
        st.session_state.pop("garmin_data",None)
        try:
            with st.spinner("Henter målinger fra Garmin Connect..."):
                raw,warnings=sync(key.strip(),days)
            st.session_state["garmin_data"]=raw
            st.session_state["garmin_warnings"]=warnings
            st.session_state["garmin_sync_time"]=pd.Timestamp.now()
        except Exception as e:
            status=getattr(e,"status_code",None)
            st.error(f"Garmin-synkronisering mislykkedes ({type(e).__name__}, status {status or 'ukendt'}). Kontrollér nøgle, netværk og API-adgang.")
    if "garmin_data" not in st.session_state:
        st.info("Indtast din nøgle i sidepanelet og hent data.")
        st.stop()
    st.sidebar.caption("Senest hentet: "+str(st.session_state["garmin_sync_time"]))
    for warning in st.session_state.get("garmin_warnings",[]):
        st.sidebar.warning(warning)
    st.caption("Garmin HRV: gennemsnit for seneste nat (ikke direkte sammenligneligt med Apple SDNN).")
try:
    if source=="Garmin Connect":
        raw=st.session_state["garmin_data"]
    elif upload is None:
        raw=demo()
        st.info("Du ser syntetiske demodata.")
    elif upload.name.lower().endswith(".csv"):
        raw=normalize(pd.read_csv(upload))
    else:
        raw,sources=apple(upload.getvalue(),upload.name)
        st.sidebar.json(sources)
except Exception as e:
    st.error(f"Import mislykkedes: {e}")
    st.stop()
st.sidebar.download_button("Eksportér rå dagsdata (CSV)",raw.to_csv().encode(),"sundhedsdata.csv","text/csv")
if raw.training_minutes.notna().any() and raw.rpe.isna().any():
    st.sidebar.caption("Tilføj RPE og registrer hviledage med 0 minutter i CSV-filen for belastningsanalyse.")
data=analyze(raw)
dates=st.sidebar.date_input("Periode",(data.index.min().date(),data.index.max().date()))
if isinstance(dates,(tuple,list)) and len(dates)==2:
    d=data.loc[str(dates[0]):str(dates[1])]
else:
    d=data
if d.empty:
    st.warning("Ingen data i perioden.")
    st.stop()
def chart(cols,title,unit,bar=False):
    cols=[c for c in cols if d[c].notna().any()]
    if not cols:
        st.info("Ingen målinger: "+title)
        return
    x=d[cols].reset_index()
    fig=(px.bar if bar else px.line)(x,x="date",y=cols,title=title,labels={"date":"Dato","value":unit,"variable":"Måling"})
    fig.update_layout(hovermode="x unified",legend_title_text="")
    st.plotly_chart(fig,use_container_width=True)
def metric(col,label,unit):
    s=d[col].dropna()
    st.metric(label,"—" if s.empty else f"{s.iloc[-1]:.1f} {unit}")
    if not s.empty: st.caption(f"Seneste måling: {s.index[-1]:%d-%m-%Y}")
for c,(col,label,unit) in zip(st.columns(4),[("sleep_hours","Søvn","t"),("vo2max","VO₂ max","ml/kg/min"),("resting_hr","Hvilepuls","bpm"),("spo2","SpO₂","%")]):
    with c: metric(col,label,unit)
tabs=st.tabs(["Søvn","Hjerte og kondition","Træning","Restitution","AI-analyse","Data"])
with tabs[0]:
    chart(["sleep_hours"],"Samlet søvn","timer")
    chart(["rem_hours","light_hours","deep_hours","awake_hours"],"Søvnstadier (registrerede timer)","timer",True)
with tabs[1]:
    chart(["heart_rate","resting_hr","max_hr"],"Puls (maksimum er observeret stikprøve)","bpm")
    chart(["hrv"],"HRV","ms")
    chart(["vo2max"],"VO₂ max","ml/kg/min")
    chart(["spo2"],"Iltmætning","%")
with tabs[2]:
    chart(["training_minutes"],"Træningsvarighed","minutter",True)
    chart(["load","load_7","load_28"],"Session-RPE og glidende gennemsnit","belastningsenheder")
    st.caption("Belastning = minutter × RPE. Ingen beregning uden registreret intensitet eller eksplicit hviledag.")
with tabs[3]:
    st.caption("Reference: median af de foregående 28 dage, mindst 14 observationer. Ingen klinisk restitutionsscore.")
    for field,label,unit in [("sleep_hours","Søvn","timer"),("hrv","HRV","ms"),("resting_hr","Hvilepuls","bpm")]:
        chart([field,field+"_baseline"],label+" vs. personlig reference",unit)
        chart([field+"_delta"],label+" – afvigelse fra reference",unit)
with tabs[4]:
    corr,n=correlations(d)
    st.subheader("Eksplorative sammenhænge")
    st.plotly_chart(px.imshow(corr,zmin=-1,zmax=1,color_continuous_scale="RdBu_r",text_auto=".2f"),use_container_width=True)
    st.caption("Pearson-korrelation; mindst 10 par. next_ betyder næste kalenderdag. Korrelation er ikke kausalitet.")
    with st.expander("Antal observationer pr. sammenhæng"): st.dataframe(n)
    model=st.text_input("Lokal Ollama-model","llama3.2")
    consent=st.checkbox("Send aggregeret statistik til lokal Ollama på 127.0.0.1")
    if st.button("Generér AI-analyse",disabled=not consent):
        stats=d.select_dtypes("number").describe().round(2).to_json()
        prompt=("Analyser på dansk de aggregerede sundhedsdata. Skeln observationer fra hypoteser. "
                "Vurder datamangler, personlige referencer og sammenhænge mellem søvn, træningsbelastning og restitution. "
                "Ingen diagnoser, ingen kausale påstande eller risikable træningsråd. "
                "Data: "+stats+" Korrelationer: "+corr.round(2).to_json()+" Antal par: "+n.to_json())
        try:
            response=requests.post("http://127.0.0.1:11434/api/generate",json={"model":model,"prompt":prompt,"stream":False},timeout=(5,180),allow_redirects=False)
            response.raise_for_status()
            st.write(response.json()["response"])
        except (requests.RequestException,ValueError,KeyError) as e:
            st.error(f"Lokal AI kunne ikke gennemføres: {e}")
with tabs[5]:
    st.dataframe(d)
    st.download_button("Eksportér analyse",d.to_csv().encode(),"analyse.csv","text/csv")
st.caption("Copyright 2026 Ib Helmer Nielsen • Apache-2.0")
