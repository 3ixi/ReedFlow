# 模块类型定义
MODULE_TYPES = {
    "md5": {
        "name": "MD5加密",
        "description": "将输入文本进行MD5加密",
        "icon": "lock",
        "category": "text",
        "config_fields": [
            {"name": "input", "type": "text", "label": "输入文本", "placeholder": "要加密的文本或变量 [variable]"},
            {"name": "output_var", "type": "text", "label": "输出变量名", "placeholder": "存储结果的变量名"}
        ]
    },
    "base64_encode": {
        "name": "Base64编码",
        "description": "将输入文本进行Base64编码",
        "icon": "code",
        "category": "text",
        "config_fields": [
            {"name": "input", "type": "text", "label": "输入文本", "placeholder": "要编码的文本或变量 [variable]"},
            {"name": "output_var", "type": "text", "label": "输出变量名", "placeholder": "存储结果的变量名"}
        ]
    },
    "base64_decode": {
        "name": "Base64解码",
        "description": "将Base64编码的输入文本进行解码",
        "icon": "code-slash",
        "category": "text",
        "config_fields": [
            {"name": "input", "type": "text", "label": "输入文本", "placeholder": "要解码的Base64字符串或变量 [variable]"},
            {"name": "output_var", "type": "text", "label": "输出变量名", "placeholder": "存储结果的变量名"}
        ]
    },
    "text_replace": {
        "name": "查找/替换文本",
        "description": "在文本中查找并替换指定内容",
        "icon": "search",
        "category": "text",
        "config_fields": [
            {"name": "input", "type": "text", "label": "输入文本", "placeholder": "原始文本或变量 [variable]"},
            {"name": "search", "type": "text", "label": "查找内容", "placeholder": "要查找的文本"},
            {"name": "replace", "type": "text", "label": "替换内容", "placeholder": "替换为的文本"},
            {"name": "output_var", "type": "text", "label": "输出变量名", "placeholder": "存储结果的变量名"}
        ]
    },
    "url_encode": {
        "name": "URL编码",
        "description": "将输入文本进行URL编码",
        "icon": "link",
        "category": "network",
        "config_fields": [
            {"name": "input", "type": "text", "label": "输入文本", "placeholder": "要进行URL编码的文本或变量 [variable]"},
            {"name": "output_var", "type": "text", "label": "输出变量名", "placeholder": "存储结果的变量名"}
        ]
    },
    "url_decode": {
        "name": "URL解码",
        "description": "将URL编码的输入文本进行解码",
        "icon": "link-45deg",
        "category": "network",
        "config_fields": [
            {"name": "input", "type": "text", "label": "输入文本", "placeholder": "要进行URL解码的文本或变量 [variable]"},
            {"name": "output_var", "type": "text", "label": "输出变量名", "placeholder": "存储结果的变量名"}
        ]
    },
    "http_request": {
        "name": "请求URL",
        "description": "发送HTTP请求到指定URL",
        "icon": "globe",
        "category": "network",
        "config_fields": [
            {"name": "url", "type": "text", "label": "请求URL", "placeholder": "https://example.com/api"},
            {"name": "method", "type": "select", "label": "请求方法", "options": ["GET", "POST", "PUT", "DELETE"], "default": "GET"},
            {"name": "headers", "type": "json", "label": "请求头", "placeholder": '{"Content-Type": "application/json"}'},
            {"name": "body", "type": "text", "label": "请求体", "placeholder": "请求体内容或变量 [variable]"},
            {"name": "timeout", "type": "number", "label": "请求超时(秒)", "placeholder": "请求超时时间", "default": 30},
            {"name": "use_http2", "type": "checkbox", "label": "使用HTTP/2", "default": False, "description": "启用HTTP/2协议请求"},
            {"name": "check_status", "type": "checkbox", "label": "检查状态码", "default": False, "description": "检查HTTP响应状态码是否为成功(2xx)"},
            {"name": "output_var", "type": "text", "label": "输出变量名", "placeholder": "存储响应的变量名"},
            {"name": "status_code_var", "type": "text", "label": "状态码变量名", "placeholder": "存储HTTP状态码的变量名", "description": "可选，存储HTTP响应状态码"}
        ]
    },
    "json_parse": {
        "name": "解析JSON",
        "description": "解析JSON字符串并提取数据",
        "icon": "braces",
        "category": "data",
        "config_fields": [
            {"name": "input", "type": "text", "label": "JSON字符串", "placeholder": "要解析的JSON字符串或变量 [variable]"},
            {"name": "path", "type": "text", "label": "数据路径", "placeholder": "例如: data.items[0].name"},
            {"name": "output_var", "type": "text", "label": "输出变量名", "placeholder": "存储提取数据的变量名"}
        ]
    },
    "set_variable": {
        "name": "设置变量",
        "description": "设置一个变量的值",
        "icon": "input-cursor-text",
        "category": "data",
        "config_fields": [
            {"name": "name", "type": "text", "label": "变量名", "placeholder": "变量名称"},
            {"name": "value", "type": "text", "label": "变量值", "placeholder": "变量的值或引用其他变量 [variable]"}
        ]
    },
    "text_template": {
        "name": "文本模板",
        "description": "创建一个包含变量的文本内容",
        "icon": "file-text",
        "category": "text",
        "config_fields": [
            {"name": "template", "type": "textarea", "label": "文本模板", "placeholder": "文本内容，可包含变量 [variable]"},
            {"name": "output_var", "type": "text", "label": "输出变量名", "placeholder": "存储生成文本的变量名"}
        ]
    },
    "notification": {
        "name": "通知服务",
        "description": "发送通知消息",
        "icon": "bell",
        "category": "data",
        "config_fields": [
            {"name": "type", "type": "select", "label": "通知类型", "options": ["email", "wxpusher", "pushplus"], "default": "email"},
            {"name": "title", "type": "text", "label": "通知标题", "placeholder": "通知标题"},
            {"name": "content", "type": "textarea", "label": "通知内容", "placeholder": "通知内容，可包含变量 [variable]"},
            {"name": "to", "type": "text", "label": "接收者", "placeholder": "邮箱地址、wxpusher的UID或pushplus的topic"}
        ]
    },
    "account_config": {
        "name": "账号配置",
        "description": "读取或更新账号配置信息",
        "icon": "person-badge",
        "category": "data",
        "config_fields": [
            {"name": "action", "type": "select", "label": "操作类型", "options": ["读取", "更新"], "default": "读取"},
            {"name": "category", "type": "select", "label": "配置类别", "options": ["静态Token", "动态Token", "其他信息"], "default": "静态Token"},
            {"name": "service", "type": "text", "label": "服务名称", "placeholder": "如: weibo, alipay, custom_service"},
            {"name": "account_name", "type": "text", "label": "配置名称", "placeholder": "如: default, test, production"},
            {"name": "field", "type": "select", "label": "配置字段", "options": ["用户名", "密码", "token", "过期时间"], "default": "用户名"},
            {"name": "value", "type": "text", "label": "写入变量", "placeholder": "要写入的值或变量 [variable]，仅更新操作时需要"},
            {"name": "output_var", "type": "text", "label": "输出变量名", "placeholder": "存储读取结果的变量名，仅读取操作时需要"}
        ]
    },
    "delay": {
        "name": "间隔时间",
        "description": "设置等待间隔时间后执行下一个模块",
        "icon": "hourglass-split",
        "category": "data",
        "config_fields": [
            {"name": "seconds", "type": "number", "label": "等待秒数", "placeholder": "等待的秒数", "default": 5}
        ]
    },
    "aes_encrypt": {
        "name": "AES加密",
        "description": "使用AES算法对文本进行加密",
        "icon": "shield-lock",
        "category": "text",
        "config_fields": [
            {"name": "input", "type": "text", "label": "输入文本", "placeholder": "要加密的文本或变量 [variable]"},
            {"name": "key", "type": "text", "label": "密钥", "placeholder": "16/24/32位字符的加密密钥或变量 [variable]"},
            {"name": "mode", "type": "select", "label": "加密模式", "options": ["ECB", "CBC"], "default": "ECB"},
            {"name": "iv", "type": "text", "label": "初始向量(IV)", "placeholder": "CBC模式下的16位初始向量，可选", "description": "仅CBC模式下需要，为空时使用全零IV"},
            {"name": "encoding", "type": "select", "label": "输出编码", "options": ["base64", "hex"], "default": "base64"},
            {"name": "output_var", "type": "text", "label": "输出变量名", "placeholder": "存储结果的变量名"}
        ]
    },
    "aes_decrypt": {
        "name": "AES解密",
        "description": "使用AES算法解密已加密文本",
        "icon": "shield-lock-fill",
        "category": "text",
        "config_fields": [
            {"name": "input", "type": "text", "label": "输入文本", "placeholder": "要解密的文本或变量 [variable]"},
            {"name": "key", "type": "text", "label": "密钥", "placeholder": "16/24/32位字符的解密密钥或变量 [variable]"},
            {"name": "mode", "type": "select", "label": "解密模式", "options": ["ECB", "CBC"], "default": "ECB"},
            {"name": "iv", "type": "text", "label": "初始向量(IV)", "placeholder": "CBC模式下的16位初始向量，可选", "description": "仅CBC模式下需要，为空时使用全零IV"},
            {"name": "encoding", "type": "select", "label": "输入编码", "options": ["base64", "hex"], "default": "base64"},
            {"name": "output_var", "type": "text", "label": "输出变量名", "placeholder": "存储结果的变量名"}
        ]
    },
    "condition": {
        "name": "条件判断",
        "description": "根据条件判断执行不同的路径",
        "icon": "question-diamond",
        "category": "data",
        "config_fields": [
            {"name": "input", "type": "text", "label": "输入值", "placeholder": "要判断的值或变量 [variable]"},
            {"name": "condition", "type": "select", "label": "条件", "options": ["包含", "等于", "大于", "小于", "不包含", "为空"], "default": "等于"},
            {"name": "compare_value", "type": "text", "label": "比较值", "placeholder": "比较的值或变量 [variable]，'为空'条件时可不填"},
            {"name": "true_branch", "type": "text", "label": "条件成立时标记", "placeholder": "条件成立时的分支标记，如 if_true", "default": "if_true"},
            {"name": "false_branch", "type": "text", "label": "条件不成立时标记", "placeholder": "条件不成立时的分支标记，如 if_false", "default": "if_false"}
        ]
    },
    "condition_end": {
        "name": "结束条件判断",
        "description": "标记条件判断的结束位置",
        "icon": "signpost-split",
        "category": "data",
        "config_fields": []
    },
    "repeat": {
        "name": "重复操作",
        "description": "重复执行指定模块",
        "icon": "arrow-repeat",
        "category": "data",
        "config_fields": [
            {"name": "target_module", "type": "text", "label": "目标模块序号", "placeholder": "要重复执行的模块序号，如 2"},
            {"name": "times", "type": "number", "label": "重复次数", "placeholder": "重复执行的次数", "default": 1},
            {"name": "interval", "type": "number", "label": "间隔时间(秒)", "placeholder": "每次执行的间隔时间", "default": 0}
        ]
    },
    "random_number": {
        "name": "随机数",
        "description": "生成指定范围内的随机数",
        "icon": "shuffle",
        "category": "data",
        "config_fields": [
            {"name": "type", "type": "select", "label": "随机数类型", "options": ["整数", "字符串"], "default": "整数"},
            {"name": "min", "type": "number", "label": "最小值", "placeholder": "随机数的最小值", "default": 1, "description": "仅整数类型时有效"},
            {"name": "max", "type": "number", "label": "最大值", "placeholder": "随机数的最大值", "default": 100, "description": "仅整数类型时有效"},
            {"name": "length", "type": "number", "label": "字符串长度", "placeholder": "随机字符串的长度", "default": 8, "description": "仅字符串类型时有效"},
            {"name": "chars", "type": "select", "label": "字符类型", "options": ["数字", "字母", "数字+字母", "数字+字母+符号"], "default": "数字+字母", "description": "仅字符串类型时有效"},
            {"name": "output_var", "type": "text", "label": "输出变量名", "placeholder": "存储随机数结果的变量名"}
        ]
    },
    "timestamp": {
        "name": "时间戳",
        "description": "获取当前时间或将指定时间转为时间戳",
        "icon": "calendar-date",
        "category": "data",
        "config_fields": [
            {"name": "action", "type": "select", "label": "操作类型", "options": ["获取当前时间", "转换时间字符串"], "default": "获取当前时间"},
            {"name": "format", "type": "select", "label": "输出格式", "options": ["时间戳(秒)", "时间戳(毫秒)", "格式化时间"], "default": "时间戳(秒)"},
            {"name": "datetime_format", "type": "text", "label": "日期格式", "placeholder": "如: %Y-%m-%d %H:%M:%S", "default": "%Y-%m-%d %H:%M:%S", "description": "当输出格式为'格式化时间'时生效"},
            {"name": "input_time", "type": "text", "label": "输入时间", "placeholder": "要转换的时间字符串或变量 [variable]", "description": "当操作类型为'转换时间字符串'时必填"},
            {"name": "input_format", "type": "text", "label": "输入格式", "placeholder": "如: %Y-%m-%d %H:%M:%S", "default": "%Y-%m-%d %H:%M:%S", "description": "当操作类型为'转换时间字符串'时必填"},
            {"name": "output_var", "type": "text", "label": "输出变量名", "placeholder": "存储时间结果的变量名"}
        ]
    },
    "system_proxy": {
        "name": "系统代理",
        "description": "设置HTTP代理，影响后续模块的网络请求",
        "icon": "ethernet",
        "category": "network",
        "config_fields": [
            {"name": "proxy_url", "type": "text", "label": "代理URL", "placeholder": "http://username:password@proxy.example.com:8080"},
            {"name": "scope", "type": "select", "label": "影响范围", "options": ["全局", "仅当前分支"], "default": "全局"},
            {"name": "reset", "type": "checkbox", "label": "重置代理", "default": False, "description": "勾选将清除已设置的代理"}
        ]
    },
    "calculate": {
        "name": "计算",
        "description": "对两个变量或变量与固定数字进行四则运算",
        "icon": "calculator",
        "category": "data",
        "config_fields": [
            {"name": "input1", "type": "text", "label": "第一个数值", "placeholder": "第一个数值或变量 [variable]"},
            {"name": "operator", "type": "select", "label": "运算符", "options": ["+", "-", "*", "/"], "default": "+"},
            {"name": "input2", "type": "text", "label": "第二个数值", "placeholder": "第二个数值或变量 [variable]"},
            {"name": "output_var", "type": "text", "label": "输出变量名", "placeholder": "存储计算结果的变量名"}
        ]
    },
    "check_domains": {
        "name": "检查域名",
        "description": "检查多个域名中哪个可用并返回结果",
        "icon": "globe-americas",
        "category": "network",
        "config_fields": [
            {"name": "domains", "type": "textarea", "label": "域名列表", "placeholder": "输入要检查的域名列表，每行一个域名，如:\nexample.com\nexample.org", "description": "每行输入一个域名，不需要添加http://或https://前缀"},
            {"name": "port", "type": "number", "label": "端口", "placeholder": "连接端口，默认为80", "default": 80},
            {"name": "timeout", "type": "number", "label": "超时时间(秒)", "placeholder": "连接超时时间", "default": 5},
            {"name": "output_var", "type": "text", "label": "输出变量名", "placeholder": "存储首个可用域名的变量名"},
            {"name": "all_results_var", "type": "text", "label": "所有结果变量名", "placeholder": "存储所有域名检查结果的变量名", "description": "可选，将以JSON格式存储所有域名的检查结果"}
        ]
    },
    "number_format": {
        "name": "数字类型",
        "description": "设置数字为整数或指定小数位数",
        "icon": "123",
        "category": "data",
        "config_fields": [
            {"name": "input", "type": "text", "label": "输入数值", "placeholder": "要格式化的数值或变量 [variable]"},
            {"name": "format_type", "type": "select", "label": "格式化类型", "options": ["保留小数位数", "进一法取整", "四舍五入取整", "舍弃小数取整"], "default": "保留小数位数"},
            {"name": "decimal_places", "type": "number", "label": "小数位数", "placeholder": "保留的小数位数", "default": 2, "description": "仅在'保留小数位数'类型下生效"},
            {"name": "output_var", "type": "text", "label": "输出变量名", "placeholder": "存储格式化后数值的变量名"}
        ]
    }
}

def get_all_module_types():
    """获取所有可用的模块类型定义"""
    return MODULE_TYPES 