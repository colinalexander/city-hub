import argparse
import sys

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from loguru import logger
from uvicorn import run

from api_resources import ChatbotRequest, ChatbotResponse, get_response_schema, get_response
from cityhub_agent import get_cityhub_agent

from langchain_core.runnables import RunnableConfig
config = RunnableConfig(recursion_limit=8)

# define the fastAPI app
app = FastAPI(
    title="CityHub API",
    version="1.0",
    description="CityHub API that retrun the chatbot response",
)

origins = [
    "http://localhost:3000", # Replace with the URL of your Next.js application
    # Add other allowed origins if needed
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

cityhub_agent = get_cityhub_agent()

RESPONSES = get_response_schema()

@app.post("/askcityhub", response_model=ChatbotResponse, responses=RESPONSES)
async def get_chatbot_result(user_request: ChatbotRequest) -> JSONResponse:
    question = user_request.question
    logger.info(f"Receive User question: {question}")
    if not isinstance(question, str):
        response = get_response(400)
        response["body"].update({"message": "the `question` should be string"})
        logger.error(f"{response=}")
        return JSONResponse(
            content=response["body"], status_code=response["status_code"]
        )

    try:
        # app logic
        inputs = {"question": question}
        #inputs = {"question": "How to apply for the slow street program in SF?"}
        for output in cityhub_agent.stream(inputs, config):
            #print(output.items())
            for key, value in output.items():
                logger.info(f"Finished running: {key}")
        final_response = value["generation"]
        logger.info(f"{final_response=}")
        #final_response = "abc"
        return JSONResponse(
            content=final_response, status_code=200
        )
    except Exception as error:
        response = get_response(500)
        response["body"].update({"message": f"{str(error)}"})
        logger.error(f"{response=}")
        return JSONResponse(
            content="Sorry, I don't know. Please try rephrasing the question.", status_code=response["status_code"]
        )



if __name__ == "__main__":
    ENV = 'local'
    parser = argparse.ArgumentParser(
        description="Run the application with customized settings."
    )
    parser.add_argument(
        "--app", default="main:app", help="The application entry point."
    )
    parser.add_argument("--port", type=int, default=9100, help="The port number.")
    parser.add_argument("--host", default="0.0.0.0", help="The host address.")
    parser.add_argument(
        "--reload",
        type=bool,
        default=True if ENV == "local" else False,
        help="Enable or disable reloading.",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="DEBUG",
        help="Set the logging level. In prod, this is ignored and set to INFO.",
    )

    args = parser.parse_args()

    APP = args.app
    PORT = args.port
    HOST = args.host
    RELOAD = args.reload
    LOG_LEVEL = args.log_level

    # Set log level.
    logger.remove(0)
    logger.add(sink=sys.stdout, level=LOG_LEVEL)
    logger.info(f"Logging level set to {LOG_LEVEL}.")


    # Otherwise try to run the app.
    try:
        logger.info(f"Running app: {APP}, {PORT=}, {HOST=}, {RELOAD=}")
        run(APP, port=PORT, host=HOST, reload=RELOAD)
    except Exception as e:
        logger.error(f"Error running app: {e}")
        raise e

# inputs = {"question": "How to apply for the slow street program in SF?"}
# for output in cityhub_agent.stream(inputs):
#     #print(output.items())
#     for key, value in output.items():
#         print(f"Finished running: {key}")
# print(value["generation"])

#print(retriever.invoke("How to apply for the Slow Streets Program"))