
import os

DEEPSEEK_API = {
    "base_url": "https://api.deepseek.com/v1",
    "model": "deepseek-chat",
    "api_key": os.getenv("DEEPSEEK_API_KEY", "default_key_here"),
    "timeout": 600,
    "max_retries": 3
}

AI_STRATEGY = {
    "enable": True,
    "min_code_length": 100,
    "scopes": ["algorithm_recognition", "dynamic_key_analysis", "custom_function_analysis"],
    "analysis_level": 2,
    "risk_assessment": True
}

AI_CONSTANTS = {
    "MAX_RETRIES": 3,
    "BASE_TIMEOUT": 600,
    "MAX_THREADS": 10
}

AI_PROMPTS = {
    "algorithm": (
        '''请严格按以下JSON格式响应：
        {{
            "对称加密": {{
                "算法": "", 
                "模式": ""
            }},
            "非对称加密": {{
                "算法": "",
                "密钥长度": "",
                "填充模式": ""
            }},
            "哈希算法": {{
                "算法": ""
            }},
            "自定义特征": []
        }}
        代码：
        ```javascript
        {code}
        ```'''
    ),
    "key": (
        '''你必须是严格的JSON生成器，按以下格式响应：{{"动态因子":[],"流程":""}}
        代码：
        ```javascript
        {code}
        ```'''
    ),
    "custom": (
        '''你必须是严格的JSON生成器，按以下格式响应：{{"自定义函数":[],"魔改特征":[]}}
        代码：
        ```javascript
        {code}
        ```'''
    )
}

AI_SETTINGS = {
    "max_code_length": 60000,
    "enable_cache": True
}