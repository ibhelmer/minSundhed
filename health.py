# Copyright 2026 Ib Helmer Nielsen
# SPDX-License-Identifier: Apache-2.0
import io
import zipfile
from collections import defaultdict
from datetime import datetime
import numpy as np
import pandas as pd
from defusedxml.ElementTree import iterparse

FIELDS = "sleep_hours rem_hours light_hours deep_hours awake_hours vo2max heart_rate resting_hr max_hr spo2 hrv training_minutes rpe".split()
TYPES = {"VO2Max":"vo2max","HeartRate":"heart_rate","RestingHeartRate":"resting_hr","OxygenSaturation":"spo2","HeartRateVariabilitySDNN":"hrv"}
STAGES = {"AsleepREM":"rem_hours","AsleepCore":"light_hours","AsleepDeep":"deep_hours","Awake":"awake_hours","AsleepUnspecified":"unspecified","Asleep":"unspecified"}

def normalize(df):
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="raise").dt.normalize()
    if df.empty or df.date.isna().any() or df.date.duplicated().any():
        raise ValueError("CSV skal have unikke, gyldige datoer.")
    for c in FIELDS:
        df[c] = pd.to_numeric(df.get(c, np.nan), errors="coerce")
        df[c] = df[c].where(np.isfinite(df[c]) & (df[c] >= 0))
    for c, upper in {"sleep_hours":24,"rem_hours":24,"light_hours":24,"deep_hours":24,"awake_hours":24,"spo2":100,"rpe":10,"training_minutes":1440}.items():
        df[c] = df[c].where(df[c] <= upper)
    return df.set_index("date")[FIELDS].sort_index().asfreq("D")

def demo():
    r = np.random.default_rng(42)
    n = 90
    sleep = r.uniform(6,9,n)
    minutes = r.choice([0,30,45,60,90],n)
    return normalize(pd.DataFrame(dict(date=pd.date_range(end=pd.Timestamp.today().normalize(),periods=n),
        sleep_hours=sleep,rem_hours=sleep*.23,light_hours=sleep*.55,deep_hours=sleep*.22,awake_hours=r.uniform(.1,.7,n),
        vo2max=43+np.arange(n)*.025+r.normal(0,.3,n),heart_rate=r.normal(70,4,n),resting_hr=r.normal(58,3,n),
        max_hr=np.where(minutes>0,r.uniform(140,180,n),r.uniform(90,120,n)),spo2=r.uniform(96,99,n),
        hrv=40+sleep*2+r.normal(0,5,n),training_minutes=minutes,rpe=np.where(minutes>0,r.integers(3,9,n),0))))

def apple(data, filename):
    archive = None
    if filename.lower().endswith(".zip"):
        archive = zipfile.ZipFile(io.BytesIO(data))
        names = [x for x in archive.infolist() if x.filename.rsplit("/",1)[-1]=="export.xml"]
        if len(names)!=1 or names[0].file_size>512*1024**2:
            raise ValueError("ZIP skal indeholde én export.xml på højst 512 MB.")
        stream=archive.open(names[0])
    else:
        stream=io.BytesIO(data)
    measurements=defaultdict(lambda:defaultdict(list))
    sleep=defaultdict(list)
    workouts=defaultdict(list)
    try:
        context=iterparse(stream,events=("start","end"))
        _,root=next(context)
        for event,e in context:
            if event!="end": continue
            a=e.attrib
            if e.tag in ("Record","Workout"):
                try:
                    start=datetime.fromisoformat(a["startDate"])
                    end=datetime.fromisoformat(a["endDate"])
                    source=a.get("sourceName","Ukendt")
                    day=end.date()
                    if e.tag=="Workout":
                        workouts[source].append((start,end))
                    elif a.get("type")=="HKCategoryTypeIdentifierSleepAnalysis":
                        stage=STAGES.get(a.get("value","").replace("HKCategoryValueSleepAnalysis",""))
                        if stage and end>start: sleep[source].append((start,end,stage))
                    else:
                        field=TYPES.get(a.get("type","").replace("HKQuantityTypeIdentifier",""))
                        if field:
                            v=float(a["value"])
                            if field=="spo2" and a.get("unit") in ("%",None) and v<=1: v*=100
                            if np.isfinite(v): measurements[field][source].append((day,v))
                except (ValueError,KeyError,TypeError): pass
                root.clear()
    finally:
        stream.close()
        if archive: archive.close()
    rows=defaultdict(dict)
    sources={}
    for field,options in measurements.items():
        source=max(options,key=lambda s:len(options[s]))
        sources[field]=source
        daily=defaultdict(list)
        for day,v in options[source]: daily[day].append(v)
        for day,values in daily.items():
            rows[day][field]=np.mean(values)
            if field=="heart_rate": rows[day]["max_hr"]=max(values)
    if sleep:
        source=max(sleep,key=lambda s:len(sleep[s]))
        sources["sleep"]=source
        # Partition overlapping records, prefer specific stages over unspecified.
        # Attribute overnight episodes to the date of their last interval.
        groups=[]
        for start,end,stage in sorted(set(sleep[source])):
            if not groups or (start-groups[-1][1]).total_seconds()>7200:
                groups.append([[(start,end,stage)],end])
            else:
                groups[-1][0].append((start,end,stage))
                groups[-1][1]=max(groups[-1][1],end)
        for intervals,end in groups:
            day=end.date()
            bounds=sorted({t for a,b,_ in intervals for t in (a,b)})
            for a,b in zip(bounds,bounds[1:]):
                stages={s for x,y,s in intervals if x<=a and y>=b}
                if not stages: continue
                specific=stages-{"unspecified"}
                stage=next(iter(specific)) if len(specific)==1 else "unspecified" if not specific or "awake_hours" not in specific else "awake_hours"
                hours=(b-a).total_seconds()/3600
                if stage!="unspecified": rows[day][stage]=rows[day].get(stage,0)+hours
                if stage!="awake_hours": rows[day]["sleep_hours"]=rows[day].get("sleep_hours",0)+hours
    if workouts:
        source=max(workouts,key=lambda s:len(workouts[s]))
        sources["workouts"]=source
        merged=[]
        for a,b in sorted(set(workouts[source])):
            if b<=a: continue
            if merged and a<=merged[-1][1]: merged[-1][1]=max(b,merged[-1][1])
            else: merged.append([a,b])
        for a,b in merged:
            day=b.date()
            rows[day]["training_minutes"]=rows[day].get("training_minutes",0)+(b-a).total_seconds()/60
    if not rows: raise ValueError("Ingen understøttede målinger fundet.")
    return normalize(pd.DataFrame.from_dict(rows,orient="index").rename_axis("date").reset_index()),sources

def analyze(df):
    df=df.copy()
    df["load"]=df.training_minutes*df.rpe
    df.loc[df.training_minutes==0,"load"]=0
    for days in (7,28):
        df[f"load_{days}"]=df.load.rolling(days,min_periods=days).mean()
    for c in ("sleep_hours","hrv","resting_hr"):
        df[c+"_baseline"]=df[c].shift(1).rolling(28,min_periods=14).median()
        df[c+"_delta"]=df[c]-df[c+"_baseline"]
    return df

def correlations(df):
    x=df[["sleep_hours","hrv","resting_hr","load","vo2max"]].copy()
    x["next_hrv"]=x.hrv.shift(-1)
    x["next_resting_hr"]=x.resting_hr.shift(-1)
    x["next_sleep"]=x.sleep_hours.shift(-1)
    return x.corr(min_periods=10),x.notna().astype(int).T.dot(x.notna().astype(int))
