# Use the AWS base image for Python 3.10
FROM public.ecr.aws/lambda/python:3.10

# Install build-essential to get the C++ compiler and other necessary tools
RUN microdnf update -y && microdnf install -y gcc-c++ make

# Copy requirements.txt
COPY requirements.txt ${LAMBDA_TASK_ROOT}

# Install the specified packages
RUN pip install -r requirements.txt

# Copy function code
COPY lambda_function.py ${LAMBDA_TASK_ROOT}

# Set the permissions to make the file executable
RUN chmod +x lambda_function.py

# Set the CMD to your handler
CMD [ "lambda_function.lambda_handler" ]