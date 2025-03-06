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
    "min_code_length": 200,
    "scopes": ["algorithm_recognition", "dynamic_key_analysis", "custom_function_analysis"],
    "analysis_level": 3,
    "risk_assessment": True,
    "confidence_threshold": 0.8
}

AI_CONSTANTS = {
    "MAX_RETRIES": 3,
    "BASE_TIMEOUT": 600,
    "MAX_THREADS": 15
}

AI_PROMPTS = {
    "algorithm": (
        '''请严格按以下JSON格式响应：
        {
            "对称加密": {
                "算法": ["AES-256-CBC"], 
                "模式": "CBC",
                "风险因素": ["使用静态IV"]
            },
            "非对称加密": {
                "算法": "RSA",
                "密钥长度": 2048,
                "填充模式": "PKCS1v1.5",
                "风险等级": "高危"
            },
            "哈希算法": {
                "算法": ["SHA256"],
                "盐值使用": false
            },
            "特征分析": [
                {"特征": "CryptoJS.AES.decrypt", "置信度": 0.9},
                {"特征": "RSA.generate(1024)", "风险等级": "高危"}
            ]
        }
        代码示例：
        ```javascript
        {code}
        ```'''
    ),
    "risk_matrix": (
        '''生成风险矩阵，按以下格式响应：
        {
            "安全评分": 75,
            "高危项": ["RSA-1024", "ECB模式"],
            "建议措施": ["升级到AES-256-GCM", "使用PBKDF2密钥派生"]
        }
        分析以下代码：
        ```javascript
        {code}
        ```'''
    )
}

RESPONSE_SCHEMA = {
    "algorithm": {
        "type": "object",
        "properties": {
            "对称加密": {
                "type": "object",
                "properties": {
                    "算法": {"type": "array"},
                    "模式": {"type": "string"},
                    "风险因素": {"type": "array"}
                }
            }
        },
        "required": ["对称加密"]
    }
}

AI_SETTINGS = {
    "max_code_length": 60000,
    "enable_cache": True,
    "cache_ttl": 3600
}