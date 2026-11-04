"""Prepare diagnostic stimuli and packets only. Never invokes a model/API."""
import argparse
from pathlib import Path
from PIL import Image, ImageDraw
from hachi.runner import picture, text, save_once
from hachi.integrity import file_sha256

PROMPT = ('Return only JSON with an images array. Describe the shape and position in '
          'each supplied image, in presentation order, with one entry for every image '
          'including duplicates. Do not infer unseen content.')


def prepare(output, model, size):
    output = Path(output)
    if output.exists():
        raise ValueError('Use a new directory for immutable diagnostic stimuli')
    if size < 64:
        raise ValueError('Use at least 64 pixels; then freeze the same study resolution')
    output.mkdir(parents=True)
    a = Image.new('RGB',(size,size),'white'); b = a.copy()
    ImageDraw.Draw(a).ellipse((size*.1,size*.1,size*.4,size*.4),fill='black')
    ImageDraw.Draw(b).polygon([(size*.6,size*.85),(size*.85,size*.85),(size*.725,size*.55)],fill='black')
    a.save(output/'A.png'); b.save(output/'B.png')
    cases=[]
    for order in ('A','B','AB','BA','AA','BB'):
        for separator in ('adjacent','newline-diagnostic'):
            content=[text(PROMPT)]
            for i,name in enumerate(order):
                if i and separator=='newline-diagnostic': content.append(text('\n'))
                content.append(picture(output/f'{name}.png'))
            name=f'{order}-{separator}'
            save_once(output/f'{name}.request.json',{'model':model,'temperature':0,'max_tokens':256,
                      'messages':[{'role':'user','content':content}]})
            cases.append({'case':name,'expected_order':list(order),'separator':separator})
    save_once(output/'diagnostic-plan.json',{'data_kind':'technical_stimuli_not_research_demonstrations',
        'model':model,'image_size':size,'images_sha256':{n:file_sha256(output/f'{n}.png') for n in ('A','B')},
        'identities':{'A':{'shape':'circle','position':'upper left'},'B':{'shape':'triangle','position':'lower right'}},
        'cases':cases,'real_model_run_status':'not_run','production_separator_changed':False})

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('output'); parser.add_argument('--model',required=True); parser.add_argument('--size',type=int,required=True)
    args=parser.parse_args()
    prepare(args.output,args.model,args.size)
