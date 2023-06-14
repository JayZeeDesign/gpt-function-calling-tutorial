import openai
import json
import os
from dotenv import load_dotenv
from pyairtable import Table
import requests

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
rapid_api_key = os.getenv("X-RapidAPI-Key")
smart_light_api_key = os.getenv("SMART_LIGHT_API_KEY")

airtable_api_key = os.getenv("AIRTABLE_API_KEY")
table = Table(airtable_api_key, "appHojHIE4y8gVBgc", "tbldUUKZFngr78ogg")

function_descriptions = [
    {
        "name": "get_stock_movers",
        "description": "Get the stocks that has biggest price/volume moves, e.g. actives, gainers, losers, etc.",
        "parameters": {
            "type": "object",
            "properties": {
            },
        }
    },
    {
        "name": "get_stock_news",
        "description": "Get the latest news for a stock",
        "parameters": {
            "type": "object",
            "properties": {
                "performanceId": {
                    "type": "string",
                    "description": "id of the stock, which is referred as performanceID in the API"
                },
            },
            "required": ["performanceId"]
        }
    },
    {
        "name": "add_stock_news_airtable",
        "description": "Add the stock, news summary & price move to Airtable",
        "parameters": {
            "type": "object",
            "properties": {
                "stock": {
                    "type": "string",
                    "description": "stock ticker"
                },
                "move": {
                    "type": "string",
                    "description": "price move in %"
                },
                "news_summary": {
                    "type": "string",
                    "description": "news summary of the stock"
                },
            }
        }
    },
    {
        "name": "control_light",
        "description": "Turn on/off the light",
        "parameters": {
            "type": "object",
            "properties": {
                "state": {
                    "type": "string",
                    "description": "the state of the light, should be on or off",
                    "enum": ["on", "off"]
                }
            }
        }
    }
]


def add_stock_news_airtable(stock, move, news_summary):
    table.create({"stock":stock, "move%": move, "news_summary":news_summary})

def get_stock_news(performanceId):
    url = "https://morning-star.p.rapidapi.com/news/list"

    querystring = {"performanceId":performanceId}

    headers = {
        "X-RapidAPI-Key": rapid_api_key,
        "X-RapidAPI-Host": "morning-star.p.rapidapi.com"
    }

    response = requests.get(url, headers=headers, params=querystring)

    short_news_list = response.json()[:5]

    print("response:", response, " json response:", short_news_list)

    return short_news_list


def get_stock_movers():
    url = "https://morning-star.p.rapidapi.com/market/v2/get-movers"

    headers = {
        "X-RapidAPI-Key": rapid_api_key,
        "X-RapidAPI-Host": "morning-star.p.rapidapi.com"
    }

    response = requests.get(url, headers=headers)
    
    return response.json()


def control_light(state):
    token = smart_light_api_key

    headers = {
        "Authorization": f"Bearer {token}",
    }

    payload = {
        "power": state,
    }

    response = requests.put('https://api.lifx.com/v1/lights/all/state', data=payload, headers=headers)

    return response.json()


def function_call(ai_response):
    function_call = ai_response["choices"][0]["message"]["function_call"]
    function_name = function_call["name"]
    arguments = function_call["arguments"]
    if function_name == "get_stock_movers":
        return get_stock_movers()
    elif function_name == "get_stock_news":
        performanceId = eval(arguments).get("performanceId")
        return get_stock_news(performanceId)
    elif function_name == "add_stock_news_airtable":
        stock = eval(arguments).get("stock")
        news_summary = eval(arguments).get("news_summary")
        move = eval(arguments).get("move")
        return add_stock_news_airtable(stock, move, news_summary)
    elif function_name == "control_light":
        state = eval(arguments).get("state")
        return control_light(state)
    else:
        return
        

def ask_function_calling(query):
    messages = [{"role": "user", "content": query}]

    response = openai.ChatCompletion.create(
        model="gpt-4-0613",
        messages=messages,
        functions = function_descriptions,
        function_call="auto"
    )

    print(response)

    while response["choices"][0]["finish_reason"] == "function_call":
        function_response = function_call(response)
        messages.append({
            "role": "function",
            "name": response["choices"][0]["message"]["function_call"]["name"],
            "content": json.dumps(function_response)
        })

        print("messages: ", messages) 

        response = openai.ChatCompletion.create(
            model="gpt-4-0613",
            messages=messages,
            functions = function_descriptions,
            function_call="auto"
        )   

        print("response: ", response) 
    else:
        print(response)


user_query = "Turn on the light"

ask_function_calling(user_query)