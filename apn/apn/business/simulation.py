from __future__ import annotations


class OperationsSimulator:
    def __init__(self,queue_metrics:dict)->None:self.queue=queue_metrics
    def checkout(self,open_counters:int=1,added_counters:int=1,capacity_per_counter:int=3)->dict:
        before=max(1,open_counters);after=max(1,before+added_counters);peak=self.queue["peak_occupancy"]
        before_load=peak/(before*capacity_per_counter);after_load=peak/(after*capacity_per_counter)
        return {"scenario":"add_checkout_capacity","inputs":{"open_counters":before,"added_counters":added_counters,"capacity_per_counter":capacity_per_counter},
                "baseline":{"load_index":round(before_load,2),"signal":"attention"if before_load>1 else"normal"},
                "projected":{"load_index":round(after_load,2),"signal":"attention"if after_load>1 else"normal"},
                "estimated_load_reduction_pct":round((1-after_load/before_load)*100,1)if before_load else 0,
                "boundary":"A deterministic capacity scenario, not a validated forecast. Calibrate with real arrival and service-time data."}
    def aisle(self,flow_capacity_change_pct:float=20)->dict:
        return {"scenario":"increase_aisle_flow_capacity","inputs":{"flow_capacity_change_pct":flow_capacity_change_pct},
                "projected_pressure_index":round(1/(1+flow_capacity_change_pct/100),2),
                "boundary":"Relative sensitivity only; layout effects require an observed before/after experiment."}
