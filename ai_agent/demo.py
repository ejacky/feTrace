from typing import *
 
import json
 
from openai import OpenAI
 
 
client = OpenAI(
    api_key="MOONSHOT_API_KEY", # 在这里将 MOONSHOT_API_KEY 替换为你从 Kimi 开放平台申请的 API Key
    base_url="https://api.moonshot.cn/v1",
)
 
tools = [
	{
		"type": "function", # 约定的字段 type，目前支持 function 作为值
		"function": { # 当 type 为 function 时，使用 function 字段定义具体的函数内容
			"name": "search", # 函数的名称，请使用英文大小写字母、数据加上减号和下划线作为函数名称
			"description": """ 
				通过搜索引擎搜索互联网上的内容。
 
				当你的知识无法回答用户提出的问题，或用户请求你进行联网搜索时，调用此工具。请从与用户的对话中提取用户想要搜索的内容作为 query 参数的值。
				搜索结果包含网站的标题、网站的地址（URL）以及网站简介。
			""", # 函数的介绍，在这里写上函数的具体作用以及使用场景，以便 Kimi 大模型能正确地选择使用哪些函数
			"parameters": { # 使用 parameters 字段来定义函数接收的参数
				"type": "object", # 固定使用 type: object 来使 Kimi 大模型生成一个 JSON Object 参数
				"required": ["query"], # 使用 required 字段告诉 Kimi 大模型哪些参数是必填项
				"properties": { # properties 中是具体的参数定义，你可以定义多个参数
					"query": { # 在这里，key 是参数名称，value 是参数的具体定义
						"type": "string", # 使用 type 定义参数类型
						"description": """
							用户搜索的内容，请从用户的提问或聊天上下文中提取。
						""" # 使用 description 描述参数以便 Kimi 大模型更好地生成参数
					}
				}
			}
		}
	},
	{
		"type": "function", # 约定的字段 type，目前支持 function 作为值
		"function": { # 当 type 为 function 时，使用 function 字段定义具体的函数内容
			"name": "crawl", # 函数的名称，请使用英文大小写字母、数据加上减号和下划线作为函数名称
			"description": """
				根据网站地址（URL）获取网页内容。
			""", # 函数的介绍，在这里写上函数的具体作用以及使用场景，以便 Kimi 大模型能正确地选择使用哪些函数
			"parameters": { # 使用 parameters 字段来定义函数接收的参数
				"type": "object", # 固定使用 type: object 来使 Kimi 大模型生成一个 JSON Object 参数
				"required": ["url"], # 使用 required 字段告诉 Kimi 大模型哪些参数是必填项
				"properties": { # properties 中是具体的参数定义，你可以定义多个参数
					"url": { # 在这里，key 是参数名称，value 是参数的具体定义
						"type": "string", # 使用 type 定义参数类型
						"description": """
							需要获取内容的网站地址（URL），通常情况下从搜索结果中可以获取网站的地址。
						""" # 使用 description 描述参数以便 Kimi 大模型更好地生成参数
					}
				}
			}
		}
	}
]
 
 
def search_impl(query: str) -> List[Dict[str, Any]]:
    """
    search_impl 使用搜索引擎对 query 进行搜索，目前主流的搜索引擎（例如 Bing）都提供了 API 调用方式，你可以自行选择
    你喜欢的搜索引擎 API 进行调用，并将返回结果中的网站标题、网站链接、网站简介信息放置在一个 dict 中返回。
 
    这里只是一个简单的示例，你可能需要编写一些鉴权、校验、解析的代码。
    """
    r = httpx.get("https://your.search.api", params={"query": query})
    return r.json()
 
 
def search(arguments: Dict[str, Any]) -> Any:
    query = arguments["query"]
    result = search_impl(query)
    return {"result": result}
 
 
def crawl_impl(url: str) -> str:
    """
    crawl_url 根据 url 获取网页上的内容。
 
    这里只是一个简单的示例，在实际的网页抓取过程中，你可能需要编写更多的代码来适配复杂的情况，例如异步加载的数据等；同时，在获取
    网页内容后，你可以根据自己的需要对网页内容进行清洗，只保留文本或移除不必要的内容（例如广告信息等）。
    """
    r = httpx.get(url)
    return r.text
 
 
def crawl(arguments: dict) -> str:
    url = arguments["url"]
    content = crawl_impl(url)
    return {"content": content}
 
 
# 通过 tool_map 将每个工具名称及其对应的函数进行映射，以便在 Kimi 大模型返回 tool_calls 时能快速找到应该执行的函数
tool_map = {
    "search": search,
    "crawl": crawl,
}
 
messages = [
    {"role": "system",
     "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一切涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。"},
    {"role": "user", "content": "请联网搜索 Context Caching，并告诉我它是什么。"}  # 在提问中要求 Kimi 大模型联网搜索
]
 
finish_reason = None
 
# 我们的基本流程是，带着用户的问题和 tools 向 Kimi 大模型提问，如果 Kimi 大模型返回了 finish_reason: tool_calls，则我们执行对应的 tool_calls，
# 将执行结果以 role=tool 的 message 的形式重新提交给 Kimi 大模型，Kimi 大模型根据 tool_calls 结果进行下一步内容的生成：
#
#   1. 如果 Kimi 大模型认为当前的工具调用结果已经可以回答用户问题，则返回 finish_reason: stop，我们会跳出循环，打印出 message.content；
#   2. 如果 Kimi 大模型认为当前的工具调用结果无法回答用户问题，需要再次调用工具，我们会继续在循环中执行接下来的 tool_calls，直到 finish_reason 不再是 tool_calls；
#
# 在这个过程中，只有当 finish_reason 为 stop 时，我们才会将结果返回给用户。
 
while finish_reason is None or finish_reason == "tool_calls":
    completion = client.chat.completions.create(
        model="kimi-k2-turbo-preview",
        messages=messages,
        temperature=0.6,
        tools=tools,  # <-- 我们通过 tools 参数，将定义好的 tools 提交给 Kimi 大模型
    )
    choice = completion.choices[0]
    finish_reason = choice.finish_reason
    if finish_reason == "tool_calls": # <-- 判断当前返回内容是否包含 tool_calls
        messages.append(choice.message) # <-- 我们将 Kimi 大模型返回给我们的 assistant 消息也添加到上下文中，以便于下次请求时 Kimi 大模型能理解我们的诉求
        for tool_call in choice.message.tool_calls: # <-- tool_calls 可能是多个，因此我们使用循环逐个执行
            tool_call_name = tool_call.function.name
            tool_call_arguments = json.loads(tool_call.function.arguments) # <-- arguments 是序列化后的 JSON Object，我们需要使用 json.loads 反序列化一下
            tool_function = tool_map[tool_call_name] # <-- 通过 tool_map 快速找到需要执行哪个函数
            tool_result = tool_function(tool_call_arguments)
 
            # 使用函数执行结果构造一个 role=tool 的 message，以此来向模型展示工具调用的结果；
            # 注意，我们需要在 message 中提供 tool_call_id 和 name 字段，以便 Kimi 大模型
            # 能正确匹配到对应的 tool_call。
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": tool_call_name,
                "content": json.dumps(tool_result), # <-- 我们约定使用字符串格式向 Kimi 大模型提交工具调用结果，因此在这里使用 json.dumps 将执行结果序列化成字符串
            })
 
print(choice.message.content) # <-- 在这里，我们才将模型生成的回复返回给用户