from __future__ import annotations
from datetime import datetime,timezone


def build_report(analytics)->dict:
    queue=analytics.queue();funnel=analytics.funnel();recommendations=analytics.recommendations()
    cameras={camera:analytics.comparison(camera)for camera in("CAM-01","CAM-02","CAM-03","CAM-04")}
    return {"report_id":datetime.now(timezone.utc).strftime("APN-%Y%m%d-%H%M%S"),"generated_at":datetime.now(timezone.utc).isoformat(),
            "title":"APN Operational Intelligence Report","dataset":"COMPOSED integration footage","executive_summary":f"The checkout view reached a measured peak of {queue['peak_occupancy']} simultaneous local tracks. {len(recommendations)} review recommendation(s) were produced.",
            "queue":queue,"funnel":funnel,"camera_comparisons":cameras,"recommendations":recommendations,
            "governance":["No face recognition","Local-track counts may repeat across cameras","Human approval required for operational action","Not a production forecast"]}
