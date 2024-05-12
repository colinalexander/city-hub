from typing import Dict, Any
from pydantic import BaseModel, Field

STATUS_CODES = {
    200: "success",
    400: "bad request",
    404: "request denied", 
    424: "dependency error",
    500: "internal error",
}


def get_response(status_code: int) -> Dict[str, Any]:
    return {
        "status_code": status_code,
        "body": {"description": STATUS_CODES.get(status_code, "UNKNOWN STATUS")},
    }


class ChatbotRequest(BaseModel):
    question: str = Field(alias="question")

    class Config:
        schema_extra = {
            "example": {
                "question": "How to apply for the slow street program in SF?"
            }
        }


class ChatbotResponse(BaseModel):
    status_code: int
    description: str
    body: Dict[str, Any]


def get_response_schema() -> Dict[str, Any]:
    return {
        code: {"description": description, "model": ChatbotResponse}
        for code, description in STATUS_CODES.items()
    }