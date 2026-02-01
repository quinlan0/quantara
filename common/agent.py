"""
智能体模块 - 重构版本
支持多种模型配置的统一接口
"""

import json
import datetime
from openai import OpenAI
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class ModelConfig:
    """模型配置类"""
    name: str
    api_key: str
    base_url: str
    model_name: str
    description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'name': self.name,
            'api_key': self.api_key,
            'base_url': self.base_url,
            'model_name': self.model_name,
            'description': self.description
        }


# 模型配置定义 - 固定配置，不可动态修改
MODEL_CONFIGS = {
    'qwen3-max': ModelConfig(
        name='qwen3-max',
        api_key='sk-d1d2188ede7147f7b8d4c44a4a3f874b',  # 建议替换为你的实际API密钥
        base_url='https://dashscope.aliyuncs.com/compatible-mode/v1',
        model_name='qwen3-max',
        description='阿里云通义千问3.0 Max模型'
    ),

    'qwen-flash': ModelConfig(
        name='qwen-flash',
        api_key='sk-d1d2188ede7147f7b8d4c44a4a3f874b',  # 建议替换为你的实际API密钥
        base_url='https://dashscope.aliyuncs.com/compatible-mode/v1',
        model_name='qwen-flash',
        description='阿里云通义千问Flash模型（快速响应）'
    ),
}


class Agent:
    """智能体类 - 支持多种模型配置"""

    def __init__(self, model_config: str = 'qwen3-max'):
        """
        初始化智能体

        Args:
            model_config: 模型配置名称，对应MODEL_CONFIGS中的键
        """
        if model_config not in MODEL_CONFIGS:
            available_configs = list(MODEL_CONFIGS.keys())
            raise ValueError(f"不支持的模型配置 '{model_config}'，可用配置: {available_configs}")

        self.config = MODEL_CONFIGS[model_config]
        self.model_config_name = model_config

        # 初始化OpenAI客户端
        self.client = OpenAI(
            api_key=self.config.api_key,
            base_url=self.config.base_url
        )

    @property
    def model_name(self) -> str:
        """获取当前使用的模型名称"""
        return self.config.model_name

    @property
    def config_name(self) -> str:
        """获取当前使用的配置名称"""
        return self.model_config_name

    def base_completion(self, content_dict: Dict[str, str], json_output: bool = False):
        """
        基础对话完成方法

        Args:
            content_dict: 内容字典，键为角色，值为内容
            json_output: 是否要求JSON格式输出

        Returns:
            completion: 完成结果
            inputs: 输入消息列表
            start_time: 开始时间
            finish_time: 结束时间
        """
        msgs = []
        for role, content in content_dict.items():
            msg = {'role': role, 'content': content}
            msgs.append(msg)

        inputs = msgs
        start_time = datetime.datetime.now()

        # 设置通用参数
        completion_kwargs = {
            'model': self.config.model_name,
            'messages': msgs,
            'extra_body': {"enable_search": True}
        }

        # 如果需要JSON输出，添加response_format
        if json_output:
            completion_kwargs['response_format'] = {"type": "json_object"}

        completion = self.client.chat.completions.create(**completion_kwargs)
        finish_time = datetime.datetime.now()

        return completion, inputs, start_time, finish_time

    def query(self, system_prompt: str, msg_content: str, json_output: bool = False) -> Dict[str, Any]:
        """
        查询方法

        Args:
            system_prompt: 系统提示
            msg_content: 用户消息内容
            json_output: 是否要求JSON格式输出

        Returns:
            包含回答和元数据的字典
        """
        content_dict = {
            'system': system_prompt,
            'user': msg_content
        }

        completion, inputs, start_time, finish_time = self.base_completion(
            content_dict, json_output=json_output
        )

        usage = completion.usage
        answer_str = completion.choices[0].message.content

        return {
            'answer': answer_str,
            'answer_json': json.loads(answer_str) if json_output and answer_str else None,
            'reason': completion.choices[0].finish_reason,
            'prompt_tokens': usage.prompt_tokens,
            'completion_tokens': usage.completion_tokens,
            'total_tokens': usage.total_tokens if hasattr(usage, 'total_tokens') else usage.prompt_tokens + usage.completion_tokens,
            'start_time': start_time,
            'finish_time': finish_time,
            'model_config': self.config_name,
            'model_name': self.model_name
        }

    def get_available_configs(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有可用的模型配置

        Returns:
            配置字典
        """
        return {name: config.to_dict() for name, config in MODEL_CONFIGS.items()}

    def get_current_config(self) -> Dict[str, Any]:
        """
        获取当前使用的配置

        Returns:
            当前配置字典
        """
        return self.config.to_dict()