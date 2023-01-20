# rembg on AWS Lambda

This is an experimental container to run
[rembg](https://github.com/danielgatis/rembg) on [AWS
Lambda](https://aws.amazon.com/lambda/). This is just an exercise in getting it
running; I make no representations that it is optimized, secure, stable, or
suitable for your application. These are largely just notes to myself, but I'm
posting them publicly in the spirit of open source in case it's useful to
someone else trying to get a chunky Python library with a lot of dependencies
running in a Lambda container.

## The Dockerfile

The Dockerfile starts with an AWS base image, installs dependencies,
pre-downloads the U2Net model, and includes our handler source code:

```dockerfile
FROM public.ecr.aws/lambda/python:3.9

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt --target "${LAMBDA_TASK_ROOT}"
RUN mkdir .u2net && curl -L https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2net.onnx -o .u2net/u2net.onnx
COPY app.py ${LAMBDA_TASK_ROOT}
CMD [ "app.handler" ]
```

The final Docker image is about 1.5GB.

## The Handler

The included `app.py` is a fairly example-grade wrapper around rembg with
limited error handling. It uses a cached `session` with the pre-downloaded ONNX
model included in the container image, to avoid downloading the model every time
it is called. In my testing, however, cold starts still seem to take about 20
seconds. Also note that `alpha_matting=True` seems to run very slowly in Lambda,
so is disabled.

## Build and Push to ECR

Start by making a new Elastic Container Registry repo to hold this container. In
this example I have called it `lamrembg`. Create it, and run the four commands
behind the `View push commands` button to get it pushed up to AWS, using your
region and account ID below:

```bash
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin YOURACCOUNTID.dkr.ecr.us-east-1.amazonaws.com
docker build -t lamrembg .
docker tag lamrembg:latest YOURACCOUNTID.dkr.ecr.us-east-1.amazonaws.com/lamrembg:latest
docker push YOURACCOUNTID.dkr.ecr.us-east-1.amazonaws.com/lamrembg:latest
```

**Note:** I built my container under WSL2 with Ubuntu Linux. If you are working
on an ARM/Mac OS machine, I don't know whether the Docker build will work. In
this case, you may need to build the container from an AWS Linux 2 instance or
from a CI service.

## Create Lambda Function

In the Lambda Console, go to create a new Lambda Function. Use `Container image`
as the source. Use the `Browse images` button to select the latest `lamrembg`
image in your AWS account. Leave the architecture `x86_64` and continue.

Under Configuration / General Configuration, increase the memory limit to
1792MB. It is my understanding that this is (as of Jan. 2023) the value
corresponding to one full vCPU. Increase the runtime timeout to 30sec. Save.

Under Configuraiton / Environment Variables, add a variable called
`NUMBA_DISABLE_JIT` and set it to `1`. This stops the `numba` library from
trying to write to the Lambda read-only filesystem.

Go to the Test tab in the console. Create a new event and paste the following
JSON test event in:

```json
{
  "queryStringParameters": {
    "src": "https://raw.githubusercontent.com/danielgatis/rembg/master/examples/animal-1.jpg"
  }
}
```

Save the event with a name of your choosing, and click `Test`. If it succeeds,
you'll get a bunch of indescript Base64 text back. Hooray!

If you'd like to see the image, go to Configuration / Function URL, and click
`Create Function URL` with `NONE` authentication. **Be aware**, you are opening
your function up to the public internet by doing this, and are responsible for
any costs if someone discovers your Function URL.

Copy your Function URL into a new browser window, and append the source image to
the query string with `?src=SOURCEURL` like this:

`https://exampleexampleexampleexamplect4z.lambda-url.us-east-1.on.aws/?src=https://raw.githubusercontent.com/danielgatis/rembg/master/examples/animal-1.jpg`

With any luck, you'll get back the test image with the background removed. In my
testing, this test image completed processing in about 2.3sec.

## License

The example handler and Dockerfile provided here are licensed under an MIT-0
license. Feel free to use and adapt for own purposes, commercial or otherwise.

## Future Directions / Open Questions

* Do the `OpenBLAS WARNING` messages in the log on startup matter? Doesn't seem
  like it.
* What's the maximum image size that can safely be handled with this amount of
  RAM?
* Can this scale to multiple vCPUs to improve performance?
* Will this work with Lambda SnapStart? (Currently as of Jan 2023, this AWS
  feature is limited to the Java runtime. But it sure would be nice to avoid the
  brutal cold start!)
* Is there any low-hanging fruit to improve performance?
* See also: [replicate.com/cjwbw/rembg](https://replicate.com/cjwbw/rembg) for a
  serverless GPU implementation. I am not affiliated with Replicate or the user
  who posted this example, but it is another potential deployment option that
  may be of interest if you are looking to run this on Lambda.
