# Copyright 2026 Ib Helmer Nielsen
# SPDX-License-Identifier: Apache-2.0
import unittest
import pandas as pd
from health import demo, normalize, analyze, correlations, apple

class HealthTests(unittest.TestCase):
    def test_demo(self):
        d=analyze(demo())
        self.assertEqual(len(d),90)
        self.assertTrue(d.load.notna().all())
        self.assertTrue(pd.isna(d.load_7.iloc[5]))
        self.assertAlmostEqual(d.load_7.iloc[6],d.load.iloc[:7].mean())
        self.assertTrue(pd.isna(d.hrv_baseline.iloc[13]))
        self.assertAlmostEqual(d.hrv_baseline.iloc[14],d.hrv.iloc[:14].median())
        corr,n=correlations(d)
        self.assertEqual(n.loc["hrv","next_hrv"],89)
    def test_missing_days(self):
        d=analyze(normalize(pd.DataFrame({"date":["2026-01-01","2026-01-03"],"training_minutes":[0,60]})))
        self.assertEqual(d.load.iloc[0],0)
        self.assertTrue(pd.isna(d.load.iloc[1]))
        self.assertTrue(pd.isna(d.load.iloc[2]))
    def test_apple(self):
        xml=b'''<HealthData>
        <Record type="HKQuantityTypeIdentifierOxygenSaturation" sourceName="Watch" unit="%" value="0.98" startDate="2026-01-01 09:00:00 +0100" endDate="2026-01-01 09:00:00 +0100"/>
        <Record type="HKCategoryTypeIdentifierSleepAnalysis" sourceName="Watch" value="HKCategoryValueSleepAnalysisAsleepCore" startDate="2025-12-31 23:00:00 +0100" endDate="2026-01-01 02:00:00 +0100"/>
        <Record type="HKCategoryTypeIdentifierSleepAnalysis" sourceName="Watch" value="HKCategoryValueSleepAnalysisAsleepREM" startDate="2026-01-01 02:00:00 +0100" endDate="2026-01-01 03:00:00 +0100"/>
        </HealthData>'''
        d,s=apple(xml,"export.xml")
        self.assertAlmostEqual(d.spo2.iloc[0],98)
        self.assertAlmostEqual(d.sleep_hours.iloc[0],4)
        self.assertAlmostEqual(d.light_hours.iloc[0],3)

if __name__=="__main__":
    unittest.main()
