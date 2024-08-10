"""
This module contains the function get_response_from_openai, which sends a request to OpenAI's GPT-4o model and returns the response.
"""

import os
import requests
import logging

def get_response_from_openai(messages, logger):
    """
    Get a response from OpenAI's GPT-4o model
    messages: list(dict)
    logger: logging.Logger
    return: str
    """
    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}", # get the API key from the environment
                "Content-Type": "application/json",
            },
            json={
                "model": "gpt-4o",
                "messages": messages,
                "stream": False, # false means the payload will be a single response, instead of a stream of responses
            },
        )
        response.raise_for_status() # raise an exception for 4xx and 5xx status codes
        return response.json()["choices"][0]["message"]["content"]
    except requests.RequestException as e:
        logger.error(f"Failed to send request to OpenAI: {e}")
        return "I'm having trouble right now talking to OpenAI. Try again later please" # hail mary response