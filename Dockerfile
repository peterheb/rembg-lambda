FROM public.ecr.aws/lambda/python:3.9

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt --target "${LAMBDA_TASK_ROOT}"
RUN mkdir .u2net && curl -L https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2net.onnx -o .u2net/u2net.onnx
COPY app.py ${LAMBDA_TASK_ROOT}
CMD [ "app.handler" ]
