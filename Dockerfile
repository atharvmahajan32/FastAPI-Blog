FROM public.ecr.aws/lambda/python:3.13

# Copy requirements first for better caching
COPY requirements.txt ${LAMBDA_TASK_ROOT}/

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py ${LAMBDA_TASK_ROOT}/
COPY app/ ${LAMBDA_TASK_ROOT}/app/

# Set the handler (Mangum handler in app.py)
CMD ["app.app.handler"]
