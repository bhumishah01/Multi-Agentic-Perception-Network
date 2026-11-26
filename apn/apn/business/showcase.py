from __future__ import annotations
from .analytics import BusinessAnalytics
from .simulation import OperationsSimulator


def build_showcase(observations:list[dict],scenario_enabled:bool=True)->dict:
    analytics=BusinessAnalytics(observations);queue=analytics.queue();comparison=analytics.comparison("CAM-04")
    simulation=OperationsSimulator(queue).checkout(open_counters=1,added_counters=1,capacity_per_counter=3)
    hypotheses=[
      {"id":"H-ARRIVAL","label":"Arrival surge","score":.42,"state":"weakened","support":[f"Peak occupancy reached {queue['peak_occupancy']} tracks."],"contradict":[f"Within-clip peak changed by only {comparison['peak_change']} between windows."],"source":"OBSERVED"},
      {"id":"H-CAPACITY","label":"Reduced service capacity","score":.84 if scenario_enabled else .34,"state":"leading"if scenario_enabled else"unverified","support":["Staged operations feed reports Counter 2 inactive."if scenario_enabled else"No counter-status sensor is connected."],"contradict":["Camera evidence alone cannot verify staff activity."],"source":"STAGED INPUT"if scenario_enabled else"MISSING"},
      {"id":"H-SPILLBACK","label":"Aisle spillback","score":.31,"state":"weakened","support":["Checkout contains clustered tracks."],"contradict":["No calibrated aisle-boundary crossing is available."],"source":"OBSERVED"},
      {"id":"H-TRACKING","label":"Tracking inflation","score":.27,"state":"possible","support":["Short clips can fragment identities."],"contradict":["The measured occupancy peak uses simultaneous tracks, limiting repeat-count inflation."],"source":"INFERRED"},
    ]
    agents=[
      {"id":"orchestrator","name":"Master Orchestrator","task":"Decompose the operational question","result":"Requested traffic, queue, capacity, evidence and simulation analyses.","state":"complete"},
      {"id":"camera","name":"Camera Agent","task":"Locate relevant checkout interval","result":f"CAM-04: {queue['local_tracks']} local tracks; peak {queue['peak_occupancy']}.","state":"complete"},
      {"id":"flow","name":"Flow Agent","task":"Test arrival-surge hypothesis","result":f"Peak change between clip halves: {comparison['peak_change']}.","state":"complete"},
      {"id":"queue","name":"Queue Agent","task":"Measure checkout pressure","result":f"{queue['frames_at_or_above_threshold']} sampled frames met threshold {queue['threshold']}.","state":"complete"},
      {"id":"capacity","name":"Capacity Agent","task":"Inspect available service positions","result":"Counter 2 marked inactive by staged operations input."if scenario_enabled else"No service-position feed available.","state":"complete"if scenario_enabled else"blocked"},
      {"id":"verifier","name":"Verifier Agent","task":"Challenge the leading explanation","result":"Capacity hypothesis leads only when the staged counter-state input is included.","state":"complete"},
      {"id":"simulation","name":"Simulation Agent","task":"Test one additional active counter","result":f"Projected load index {simulation['baseline']['load_index']} → {simulation['projected']['load_index']}.","state":"complete"},
    ]
    return {
      "title":"Checkout pressure investigation","question":"Why did checkout pressure increase, and what should we test?","scenario_mode":scenario_enabled,
      "truth_boundary":{"observed":"Boxes, local tracks, timestamps and occupancy are measured from CAM-04.","staged":"Counter 2 inactivity and post-intervention outcome are controlled scenario inputs.","inferred":"Root-cause ranking and simulation combine measured and staged inputs."},
      "observed":{"camera_id":"CAM-04","local_tracks":queue["local_tracks"],"peak_occupancy":queue["peak_occupancy"],"mean_occupancy":queue["mean_occupancy"],"longest_visible_s":queue["longest_observed_span_s"],"threshold_frames":queue["frames_at_or_above_threshold"]},
      "spatial_memory":[{"time":"T+00","zone":"Entrance","event":"anonymous entry tracks","source":"OBSERVED"},{"time":"T+15","zone":"Main aisle","event":"local movement reconstructed","source":"OBSERVED"},{"time":"T+19","zone":"Service counter","event":"service-area tracks observed","source":"OBSERVED"},{"time":"T+22","zone":"Checkout","event":f"peak {queue['peak_occupancy']} simultaneous tracks","source":"OBSERVED"},{"time":"T+22","zone":"Operations","event":"Counter 2 inactive","source":"STAGED INPUT"}],
      "agents":agents,"hypotheses":hypotheses,
      "finding":{"label":"Reduced service capacity is the leading scenario explanation"if scenario_enabled else"Root cause remains unresolved","confidence_state":"scenario-supported"if scenario_enabled else"insufficient-evidence","explanation":"Measured checkout pressure aligns with the staged counter-inactivity event. The footage alone does not prove the cause."},
      "simulation":simulation,
      "intervention":{"id":"INT-CHECKOUT-01","action":"Open one additional staffed checkout for a supervised 10-minute pilot","success_criteria":["load index below 1.0","peak occupancy below 6","no aisle spillback","service completions improve"],"requires_human":True,"external_action_taken":False},
      "verification_preview":{"source":"STAGED OUTCOME","before":{"load_index":simulation["baseline"]["load_index"],"peak":queue["peak_occupancy"]},"after":{"load_index":simulation["projected"]["load_index"],"peak":max(2,queue["peak_occupancy"]-2)},"criteria_met":3,"criteria_total":4,"status":"preview only until approved"},
    }


def approve_showcase(showcase:dict)->dict:
    preview=showcase["verification_preview"]
    return {"intervention_id":showcase["intervention"]["id"],"status":"approved_for_staged_pilot","external_action_taken":False,
            "verification":{**preview,"status":"staged pilot verified","conclusion":"The staged outcome meets 3 of 4 success criteria. A real deployment would continue monitoring before operational adoption."}}
