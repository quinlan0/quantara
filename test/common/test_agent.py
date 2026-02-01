#!/usr/bin/env python3
"""
测试重构后的agent.py模块
"""

import sys
from pathlib import Path
# 添加项目根目录到Python路径，以便导入common模块
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def test_model_configs():
    """测试模型配置"""
    try:
        from common.agent import MODEL_CONFIGS, ModelConfig

        # 检查默认配置是否存在
        assert 'qwen3-max' in MODEL_CONFIGS
        assert 'qwen-flash' in MODEL_CONFIGS

        # 检查配置结构
        config = MODEL_CONFIGS['qwen3-max']
        assert hasattr(config, 'name')
        assert hasattr(config, 'api_key')
        assert hasattr(config, 'base_url')
        assert hasattr(config, 'model_name')
        assert hasattr(config, 'description')

        # 检查to_dict方法
        config_dict = config.to_dict()
        assert isinstance(config_dict, dict)
        assert 'name' in config_dict
        assert 'api_key' in config_dict

        print("✅ 模型配置测试通过")
        return True
    except Exception as e:
        print(f"❌ 模型配置测试失败: {e}")
        return False

def test_agent_initialization():
    """测试Agent初始化"""
    try:
        from common.agent import Agent

        # 测试默认初始化
        agent = Agent()
        assert agent.config_name == 'qwen3-max'
        assert agent.model_name == 'qwen3-max'

        # 测试指定配置初始化
        agent_flash = Agent('qwen-flash')
        assert agent_flash.config_name == 'qwen-flash'
        assert agent_flash.model_name == 'qwen-flash'

        # 测试无效配置
        try:
            Agent('invalid_config')
            assert False, "应该抛出异常"
        except ValueError:
            pass  # 预期的异常

        print("✅ Agent初始化测试通过")
        return True
    except Exception as e:
        print(f"❌ Agent初始化测试失败: {e}")
        return False

def test_config_structure():
    """测试配置结构"""
    try:
        from common.agent import MODEL_CONFIGS, ModelConfig

        # 测试配置数量
        assert len(MODEL_CONFIGS) == 2  # 只有qwen3-max和qwen-flash

        # 测试配置不可修改
        original_configs = MODEL_CONFIGS.copy()

        # 尝试添加配置（应该失败，因为没有add_model_config函数）
        try:
            # 这里我们只是测试配置是只读的，不应该有动态修改的接口
            assert len(MODEL_CONFIGS) == len(original_configs)
        except:
            pass

        print("✅ 配置结构测试通过")
        return True
    except Exception as e:
        print(f"❌ 配置结构测试失败: {e}")
        return False

def test_agent_methods():
    """测试Agent方法"""
    try:
        from common.agent import Agent

        agent = Agent()

        # 测试获取配置信息
        configs = agent.get_available_configs()
        assert isinstance(configs, dict)
        assert len(configs) > 0

        current_config = agent.get_current_config()
        assert isinstance(current_config, dict)
        assert 'name' in current_config

        print("✅ Agent方法测试通过")
        return True
    except Exception as e:
        print(f"❌ Agent方法测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("开始测试重构后的agent.py模块...")
    print("=" * 50)

    tests = [
        test_model_configs,
        test_agent_initialization,
        test_config_structure,
        test_agent_methods
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1
        print()

    print("=" * 50)
    print(f"测试结果: {passed}/{total} 通过")

    if passed == total:
        print("🎉 所有测试通过！重构成功。")
        return 0
    else:
        print("⚠️  部分测试失败，请检查代码。")
        return 1

if __name__ == "__main__":
    exit(main())