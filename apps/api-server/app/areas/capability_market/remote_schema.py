"""第三方工具schema的本地验证，禁止外部引用与模型凭据参数。"""
from hashlib import sha256
import json

from fastapi import HTTPException
from jsonschema import Draft202012Validator, validators
from jsonschema.exceptions import SchemaError, ValidationError
from referencing.exceptions import Unresolvable

from app.agent_mcp.safety import reject_credentials

_SCHEMA_MAPS = {'properties', '$defs', 'definitions', 'dependentSchemas', 'dependencies'}
_SCHEMA_VALUES = {'additionalProperties', 'additionalItems', 'unevaluatedProperties', 'unevaluatedItems',
                  'items', 'contains', 'propertyNames', 'not', 'if', 'then', 'else', 'contentSchema'}
_SCHEMA_ARRAYS = {'allOf', 'anyOf', 'oneOf', 'prefixItems'}


def schema_fingerprint(schema):
    return sha256(json.dumps(schema, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def checked_schema(schema):
    if not isinstance(schema, dict) or schema.get('type') != 'object':
        raise HTTPException(422, '远程工具参数schema必须声明object类型')
    try:
        encoded = json.dumps(schema, ensure_ascii=False, allow_nan=False)
        if len(encoded.encode()) > 32768:
            raise HTTPException(422, '远程工具参数schema超过32KB限制')
        reject_credentials(schema)

        nodes = 0
        schema_nodes = set()

        def inspect(value, depth=0, *, schema_node=False, schema_map=False, schema_array=False):
            nonlocal nodes
            nodes += 1
            if nodes > 1024 or depth > 24:
                raise HTTPException(422, '远程工具schema层级或节点数超过限制')
            if isinstance(value, dict):
                if schema_node:
                    schema_nodes.add(id(value))
                    if '$schema' in value and (not isinstance(value['$schema'], str) or validators.validator_for(value, default=None) is None):
                        raise HTTPException(422, '远程工具schema声明了不支持的规范版本')
                    if 'pattern' in value or 'patternProperties' in value:
                        raise HTTPException(422, '远程工具schema不支持正则约束，避免第三方表达式阻塞服务')
                    if '$ref' in value and (not isinstance(value['$ref'], str) or (value['$ref'] != '#' and not value['$ref'].startswith('#/'))):
                        raise HTTPException(422, '远程工具schema不允许外部引用')
                    if '$dynamicRef' in value or '$recursiveRef' in value or '$id' in value:
                        raise HTTPException(422, '远程工具schema不支持动态引用或重定义文档地址')
                # 映射键是业务名称；只有其值和标准schema子节点承载约束。
                for key, child in value.items():
                    inspect(child, depth + 1,
                            schema_node=schema_map or (schema_node and key in _SCHEMA_VALUES),
                            schema_map=schema_node and key in _SCHEMA_MAPS,
                            schema_array=schema_node and (key in _SCHEMA_ARRAYS or key == 'items'))
            elif isinstance(value, list):
                for child in value:
                    inspect(child, depth + 1, schema_node=schema_array)

        inspect(schema, schema_node=True)
        expansions = 0

        def resolve(value, references=(), depth=0):
            nonlocal expansions
            expansions += 1
            if expansions > 2048 or depth > 32:
                raise HTTPException(422, '远程工具schema引用展开超过限制')
            if isinstance(value, dict):
                if '$ref' in value:
                    reference = value['$ref']
                    if reference in references:
                        raise HTTPException(422, '远程工具schema不支持递归引用')
                    target = schema
                    try:
                        for part in reference[2:].split('/') if reference != '#' else []:
                            part = part.replace('~1', '/').replace('~0', '~')
                            target = target[int(part)] if isinstance(target, list) else target[part]
                    except (KeyError, IndexError, TypeError, ValueError):
                        raise HTTPException(422, '远程工具schema本地引用不存在') from None
                    if not isinstance(target, (dict, bool)):
                        raise HTTPException(422, '远程工具schema本地引用目标不是schema')
                    if isinstance(target, dict) and id(target) not in schema_nodes:
                        inspect(target, schema_node=True)
                    resolve(target, (*references, reference), depth + 1)
                for key, child in value.items():
                    if key in _SCHEMA_MAPS and isinstance(child, dict):
                        for subschema in child.values():
                            if isinstance(subschema, (dict, bool)):
                                resolve(subschema, references, depth + 1)
                    elif key in _SCHEMA_VALUES and isinstance(child, (dict, bool)):
                        resolve(child, references, depth + 1)
                    elif (key in _SCHEMA_ARRAYS or key == 'items') and isinstance(child, list):
                        for subschema in child:
                            if isinstance(subschema, (dict, bool)):
                                resolve(subschema, references, depth + 1)

        resolve(schema)
        validator = Draft202012Validator if '$schema' not in schema else validators.validator_for(schema, default=None)
        if validator is None:
            raise HTTPException(422, '远程工具schema声明了不支持的规范版本')
        validator.check_schema(schema)
        return validator(schema)
    except (SchemaError, ValueError, TypeError, RecursionError):
        raise HTTPException(422, '远程工具参数schema无效') from None


def validate_arguments(schema, arguments):
    if not isinstance(arguments, dict):
        raise HTTPException(422, '远程工具参数必须是JSON对象')
    reject_credentials(arguments)
    try:
        if len(json.dumps(arguments, ensure_ascii=False, allow_nan=False).encode()) > 32768:
            raise HTTPException(422, '远程工具参数超过32KB限制')
        checked_schema(schema).validate(arguments)
    except (ValidationError, Unresolvable, ValueError, TypeError, RecursionError):
        # jsonschema异常含原始输入，禁止将其带入响应或日志。
        raise HTTPException(422, '远程工具参数不符合已发现的schema') from None
