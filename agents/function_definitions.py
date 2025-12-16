"""
GLM-Realtime Function Call 定义
用于集成 Claude Code Sub Agent 系统
"""

# 定义可用的函数（Tools）
TRAVEL_ASSISTANT_FUNCTIONS = [
    {
        "type": "function",
        "name": "plan_trip",
        "description": "规划旅行行程，包括目的地、时间、景点推荐等。根据用户需求制定详细的旅行计划。",
        "parameters": {
            "type": "object",
            "properties": {
                "destination": {
                    "type": "string",
                    "description": "目的地城市或国家，例如：北京、上海、东京"
                },
                "start_date": {
                    "type": "string",
                    "description": "出发日期，格式：YYYY-MM-DD"
                },
                "end_date": {
                    "type": "string",
                    "description": "返回日期，格式：YYYY-MM-DD"
                },
                "preferences": {
                    "type": "string",
                    "description": "旅行偏好，例如：文化、美食、自然风光、购物等"
                },
                "budget": {
                    "type": "string",
                    "description": "预算范围，例如：经济型、中等、豪华"
                }
            },
            "required": ["destination", "start_date", "end_date"]
        }
    },
    {
        "type": "function",
        "name": "book_ticket",
        "description": "预订机票、火车票或汽车票。支持查询和预订各种交通工具的票务。",
        "parameters": {
            "type": "object",
            "properties": {
                "ticket_type": {
                    "type": "string",
                    "enum": ["flight", "train", "bus"],
                    "description": "票务类型：flight(飞机)、train(火车)、bus(汽车)"
                },
                "departure_city": {
                    "type": "string",
                    "description": "出发城市"
                },
                "arrival_city": {
                    "type": "string",
                    "description": "到达城市"
                },
                "departure_date": {
                    "type": "string",
                    "description": "出发日期，格式：YYYY-MM-DD"
                },
                "return_date": {
                    "type": "string",
                    "description": "返程日期（可选），格式：YYYY-MM-DD"
                },
                "passenger_count": {
                    "type": "integer",
                    "description": "乘客人数"
                },
                "seat_class": {
                    "type": "string",
                    "description": "座位等级，例如：经济舱、商务舱、头等舱"
                }
            },
            "required": ["ticket_type", "departure_city", "arrival_city", "departure_date", "passenger_count"]
        }
    },
    {
        "type": "function",
        "name": "book_hotel",
        "description": "预订酒店。支持查询和预订各种类型的住宿。",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "入住城市"
                },
                "check_in_date": {
                    "type": "string",
                    "description": "入住日期，格式：YYYY-MM-DD"
                },
                "check_out_date": {
                    "type": "string",
                    "description": "退房日期，格式：YYYY-MM-DD"
                },
                "room_count": {
                    "type": "integer",
                    "description": "房间数量"
                },
                "guest_count": {
                    "type": "integer",
                    "description": "入住人数"
                },
                "hotel_type": {
                    "type": "string",
                    "description": "酒店类型或星级，例如：经济型、三星、四星、五星"
                },
                "preferences": {
                    "type": "string",
                    "description": "特殊需求，例如：靠近市中心、有早餐、有停车场"
                }
            },
            "required": ["city", "check_in_date", "check_out_date", "room_count", "guest_count"]
        }
    }
]


def get_function_definitions():
    """获取所有函数定义"""
    return TRAVEL_ASSISTANT_FUNCTIONS


def get_function_by_name(name: str):
    """根据名称获取函数定义"""
    for func in TRAVEL_ASSISTANT_FUNCTIONS:
        if func["name"] == name:
            return func
    return None

