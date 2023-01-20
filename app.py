import base64
import json
import requests
import time
import onnxruntime as ort
from rembg.session_simple import SimpleSession
from rembg import remove

# init code
print("initializing model...")
start = time.time_ns()/1e6
sess_opts = ort.SessionOptions()
sess_opts.inter_op_num_threads = 1
session = SimpleSession("u2net", ort.InferenceSession(
    str('/var/task/.u2net/u2net.onnx'),
    providers=ort.get_available_providers(),
    sess_options=sess_opts,
),
)
print(f"model initialized: {(time.time_ns()/1e6 - start):.1f}ms")


def handler(event, context):
    print(json.dumps(event))
    src = ''
    if 'queryStringParameters' in event:
        src = event['queryStringParameters'].get('src', '')
    if src == '':
        return {
            'headers': {"Content-Type": "application/json"},
            'statusCode': 400,
            'body': json.dumps({'error': 'bad request'})
        }

    try:
        input = requests.get(src, allow_redirects=True)
        # too slow: , alpha_matting=True)
        output = remove(input.content, session=session)
        return {
            'headers': {"Content-Type": "image/png"},
            'statusCode': 200,
            'body': base64.b64encode(output).decode('utf-8'),
            'isBase64Encoded': True
        }
    except Exception as ex:
        return {
            'headers': {"Content-Type": "application/json"},
            'statusCode': 500,
            'body': json.dumps({'error': ex.__repr__()})
        }
