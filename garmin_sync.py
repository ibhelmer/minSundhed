# Copyright 2026 Ib Helmer Nielsen
# SPDX-License-Identifier: Apache-2.0
import pandas as pd
from health import normalize

def sync(key, days):
    from garmin_personal_api import GarminPersonalApiClient, PersonalApiAuthenticator
    from tempfile import TemporaryDirectory
    from pathlib import Path
    from datetime import date, timedelta
    rows=[]
    warnings=[]
    def get(fn,*args):
        try:
            return fn(*args)
        except Exception as e:
            status=getattr(e,"status_code",None)
            if status in (401,403,429): raise
            warnings.append(f"{fn.__name__}: {type(e).__name__}")
            return None
    def obj(x):
        return x if isinstance(x,dict) else {}
    def pick(x,*keys):
        return next((x[k] for k in keys if x.get(k) is not None),None)
    def hours(x):
        return x/3600 if isinstance(x,(int,float)) and x>=0 else None
    end=date.today()
    start=end-timedelta(days=days-1)
    with TemporaryDirectory() as tmp:
        with PersonalApiAuthenticator(bearer_token_cache_file=Path(tmp)/"token.json") as auth:
            token=auth.obtain_token(key)
        with GarminPersonalApiClient(token.access_token) as c:
            summaries=get(c.get_daily_summaries,start,end)
            daily={str(x.get("calendarDate")):x for x in summaries if isinstance(x,dict)} if isinstance(summaries,list) else {}
            for i in range(days):
                day=(start+timedelta(days=i)).isoformat()
                s=obj(get(c.get_daily_sleep,day))
                s=obj(s.get("dailySleepDTO",s))
                h=obj(get(c.get_daily_heart_rate,day))
                v=obj(get(c.get_daily_hrv,day))
                v=obj(v.get("hrvSummary",v))
                o=obj(get(c.get_daily_spo2,day))
                a=obj(daily.get(day))
                samples=h.get("heartRateValues") or []
                values=[p[1] for p in samples if isinstance(p,list) and len(p)>1 and isinstance(p[1],(int,float)) and p[1]>0]
                rows.append(dict(date=day,sleep_hours=hours(s.get("sleepTimeSeconds")),rem_hours=hours(s.get("remSleepSeconds")),light_hours=hours(s.get("lightSleepSeconds")),deep_hours=hours(s.get("deepSleepSeconds")),awake_hours=hours(s.get("awakeSleepSeconds")),hrv=v.get("lastNightAvg"),resting_hr=pick(h,"restingHeartRate") or a.get("restingHeartRate"),max_hr=pick(h,"maxHeartRate") or a.get("maxHeartRate"),heart_rate=sum(values)/len(values) if values else None,spo2=pick(o,"averageSpO2","averageSpo2","averageSPO2") or a.get("averageSpo2")))
            vo=get(c.get_daily_vo2_max,start,end)
            byday={r["date"]:r for r in rows}
            if isinstance(vo,list):
                for item in vo:
                    item=obj(item)
                    generic=obj(item.get("generic",item))
                    day=pick(generic,"calendarDate") or item.get("calendarDate")
                    if day in byday: byday[day]["vo2max"]=pick(generic,"vo2MaxPreciseValue","vo2MaxValue")
            offset=0
            seen=set()
            while offset<10000:
                activities=get(lambda: c.search_activities(start=offset,limit=100,start_date=start,end_date=end))
                if not isinstance(activities,list) or not activities: break
                for act in activities:
                    act=obj(act)
                    ident=act.get("activityId")
                    if ident is None or ident in seen: continue
                    seen.add(ident)
                    day=str(act.get("startTimeLocal",""))[:10]
                    duration=act.get("duration")
                    if day in byday and isinstance(duration,(int,float)) and duration>=0:
                        r=byday[day]
                        r["training_minutes"]=r.get("training_minutes",0)+duration/60
                if len(activities)<100: break
                offset+=len(activities)
    df=normalize(pd.DataFrame(rows))
    if not df.notna().any().any(): raise ValueError("Ingen genkendelige Garmin-målinger.")
    return df, sorted(set(warnings))
