"""Prompt链（Chain-of-Thought）- 多步推理"""
from typing import List, Dict, Any, Optional
from app.services.llm_service import llm_service
from app.services.prompt_engineer import prompt_engineer
from app.utils.logger import app_logger


class PromptChain:
    """Prompt链 - 支持多步推理"""
    
    def __init__(self, steps: List[Dict[str, Any]]):
        """
        初始化Prompt链
        
        Args:
            steps: 步骤列表，每个步骤包含：
                - name: 步骤名称
                - prompt_template: Prompt模板名称
                - input_mapping: 输入映射（如何从前一步获取输入）
                - output_processor: 输出处理器（可选）
        """
        self.steps = steps
    
    def execute(self, initial_input: Dict[str, Any]) -> Dict[str, Any]:
        """执行Prompt链"""
        context = initial_input.copy()
        results = []
        
        for i, step in enumerate(self.steps):
            step_name = step.get("name", f"step_{i+1}")
            prompt_template_name = step.get("prompt_template")
            input_mapping = step.get("input_mapping", {})
            output_processor = step.get("output_processor")
            
            app_logger.info(f"执行Prompt链步骤: {step_name}")
            
            # 准备输入
            step_input = {}
            for key, value in input_mapping.items():
                if isinstance(value, str):
                    # 从context中获取值
                    step_input[key] = context.get(value, value)
                else:
                    step_input[key] = value
            
            # 格式化Prompt
            prompt_data = prompt_engineer.format_prompt(
                prompt_template_name,
                **step_input
            )
            
            if not prompt_data:
                app_logger.warning(f"无法获取Prompt模板: {prompt_template_name}")
                continue
            
            # 调用LLM
            try:
                response = llm_service.generate(
                    prompt=prompt_data["user"],
                    system_prompt=prompt_data["system"],
                    temperature=0.7
                )
                
                # 处理输出
                if output_processor:
                    processed_output = output_processor(response, context)
                else:
                    processed_output = response
                
                # 更新context
                context[f"{step_name}_output"] = processed_output
                context[f"{step_name}_raw"] = response
                
                results.append({
                    "step": step_name,
                    "input": step_input,
                    "output": processed_output,
                    "raw_output": response
                })
                
            except Exception as e:
                app_logger.error(f"Prompt链步骤执行失败: {step_name}, {e}")
                results.append({
                    "step": step_name,
                    "error": str(e)
                })
                break
        
        return {
            "results": results,
            "final_context": context,
            "success": len(results) == len(self.steps) and not any("error" in r for r in results)
        }


class ComplexQuestionChain:
    """复杂问题分解链"""
    
    @staticmethod
    def create_decomposition_chain() -> PromptChain:
        """创建问题分解链"""
        steps = [
            {
                "name": "decompose",
                "prompt_template": "medical_consultation",
                "input_mapping": {
                    "question": "请将以下复杂问题分解为多个子问题：{original_question}",
                    "context": ""
                }
            },
            {
                "name": "answer_subquestions",
                "prompt_template": "medical_consultation",
                "input_mapping": {
                    "question": "{decompose_output}",
                    "context": "context"
                }
            },
            {
                "name": "synthesize",
                "prompt_template": "medical_consultation",
                "input_mapping": {
                    "question": "请综合以下回答，给出完整的答案：{answer_subquestions_output}",
                    "context": ""
                }
            }
        ]
        return PromptChain(steps)


class ReasoningChain:
    """推理链 - Chain-of-Thought"""
    
    @staticmethod
    def create_reasoning_chain() -> PromptChain:
        """创建推理链"""
        steps = [
            {
                "name": "understand",
                "prompt_template": "medical_consultation",
                "input_mapping": {
                    "question": "请理解以下问题，提取关键信息：{question}",
                    "context": "context"
                }
            },
            {
                "name": "reason",
                "prompt_template": "medical_consultation",
                "input_mapping": {
                    "question": "基于以下理解，进行推理分析：{understand_output}",
                    "context": "context"
                }
            },
            {
                "name": "conclude",
                "prompt_template": "medical_consultation",
                "input_mapping": {
                    "question": "基于以上推理，给出最终结论：{reason_output}",
                    "context": "context"
                }
            }
        ]
        return PromptChain(steps)

