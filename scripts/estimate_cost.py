import argparse
import json
from hachi.cost import estimate
p=argparse.ArgumentParser()
p.add_argument('runs'); p.add_argument('--input-per-million',type=float,required=True); p.add_argument('--output-per-million',type=float,required=True)
a=p.parse_args()
print(json.dumps(estimate(a.runs,a.input_per_million,a.output_per_million),indent=2))
