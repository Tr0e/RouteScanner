import os
import re
import pandas as pd
from colorama import Fore, init

# 配置colorama颜色自动重置，否则得手动设置Style.RESET_ALL
init(autoreset=True)

# 统计路由数量的全局变量
route_num = 1
# 正则表达式来匹配Spring的路由注解、方法返回类型、方法名称和参数
mapping_pattern = re.compile(r'@(Path|(Request|Get|Post|Put|Delete|Patch)Mapping)\(')


def write_routes_to_xlsx(all_data_list):
    """
    将路由信息写入Excel文件
    """
    data = {
        "Context": [item['context'] for item in all_data_list],
        "Parent Route": [item['parent_route'] for item in all_data_list],
        "Route": [item['route'] for item in all_data_list],
        "Request": [item['request'] for item in all_data_list],
        "Return Type": [item['return_type'] for item in all_data_list],
        "Method Name": [item['method_name'] for item in all_data_list],
        "Parameters": [item['parameters'] for item in all_data_list],
        "File Path": [item['file_path'] for item in all_data_list],
    }
    writer = pd.ExcelWriter('Data.xlsx')
    dataFrame = pd.DataFrame(data)
    dataFrame.to_excel(writer, sheet_name="password")
    writer.close()
    print(Fore.BLUE + "[*] Successfully saved data to xlsx")


def extract_request_mapping_value(s):
    """
    提取类开头的父级路由，通过@RequestMapping注解中的value字段的值，
    可能出现括号中携带除了value/path之外的字段，比如 method = RequestMethod.POST。
    也能处理@RequestMapping("/clientSideFiltering/challenge-store")这种格式。
    """
    # 匹配三种情况：带有 value、path 或者直接给出的路径
    pattern = r'@RequestMapping\(\s*(?:(?:value|path)\s*=\s*"([^"]*)"|"(\/[^"]*)")(?:,.*?)?\)'
    match = re.search(pattern, s)
    if match:
        # 返回匹配到的 'value' 或 'path' 字段，或者直接匹配到的路径
        return match.group(1) or match.group(2)
    else:
        return None


def get_class_parent_route(content):
    """
    提取类级别的父级路由
    注意有可能会返回None，比如java-sec-code-master里的CommandInject.java
    """
    parent_route = None
    content_lines = content.split('\n')
    public_class_line = None
    # 遍历每一行，找到 "public class" 所在的行
    for line_number, line in enumerate(content_lines, start=1):
        if re.search(r'public class', line):
            public_class_line = line_number
            break
    if public_class_line is not None:
        # 提取 "public class" 之前的行
        content_before_public_class = content_lines[:public_class_line]
        for line in content_before_public_class:
            if re.search(r'@RequestMapping\(', line):
                parent_route = extract_request_mapping_value(line)
    return parent_route, public_class_line


def extract_value_between_quotes(line):
    """
    提取字符串中第一个""中间的值，目的是提取@GetMapping("/upload")格式中的路由值（尚待解决的是部分项目的路由值是通过一个常量类集中定义的）
    """
    pattern = r'"(.*?)"'
    match = re.search(pattern, line)
    if match:
        value = match.group(1)
        return value
    else:
        return None


def extract_function_details(function_def):
    """
    从函数定义的行级代码，解析并返回一个函数的详细信息，包括返回类型、函数名、参数等
    """
    # print(function_def)
    pattern = re.compile(
        # r'public\s+(?:@\w+\s+)*([\w<>\[\],\s]+)\s+(\w+)\s*\((.*)\)'
        r'public\s+(?:@\w+(?:\([^)]*\))?\s+)*([\w<>\[\],\s\?]+)\s+(\w+)\s*\((.*)\)\s*(?:throws\s+[\w<>,\s]+)?\s*{?'
    )
    # 匹配函数签名
    match = pattern.search(function_def)
    if match:
        return_type = match.group(1)  # 返回类型
        function_name = match.group(2)  # 函数名
        parameters = match.group(3)  # 参数
        return return_type, function_name, parameters
    else:
        return None, None, None


def find_constant_value(folder_path, constant_name):
    """
    提取出路由的常量值
    """
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.endswith('.java'):
                file_path = os.path.join(root, file)
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    pattern = fr'static\s+final\s+String\s+{constant_name}\s*=\s*"(.*?)";'
                    match = re.search(pattern, content)
                    if match:
                        return match.group(1)
    return None


def get_path_value(line, directory):
    """
    提取出路由的值，适配通过字符串直接提供的路由值，或者通过常量提供的路由值，比如：
    @GetMapping(path = "/server-directory")、@GetMapping(path = URL_HINTS_MVC, produces = "application/json")、@GetMapping(value = "/server-directory")
    """
    pattern = r'\((?:path|value)\s*=\s*(?:"([^"]*)"|([A-Z_]+))'
    matches = re.findall(pattern, line)
    route = ''
    for match in matches:
        if match[0]:  # 提取出path为字符串的值
            route = match[0]
            # print(Fore.GREEN + route)
        elif match[1]:  # 提取出path为常量的值
            route = find_constant_value(directory, match[1])
            # print(Fore.BLUE + route)
    return route


def get_request_type(route_define):
    """
    从路由定义的注解中，提取出API请求类型，比如GET、POST等
    """
    # print(route_define)
    if route_define.startswith('@RequestMapping'):
        # 提取@RequestMapping注解中的method字段的值
        if route_define.find('method =') > -1:
            request_type = (str(route_define.split('method =')[1]).split('}')[0].strip().replace('{', '').replace(')', '')).replace('RequestMethod.', '')
        # 未指定具体请求类型的RequestMapping注解，则默认为支持所有请求类型
        else:
            request_type = 'All'
    else:
        request_type = route_define.split('Mapping')[0][1:]
    return request_type


def extract_context_path(directory):
    """
    从application.properties或xxx.yml等Java项目配置文件中提取上下文路径
    """
    for dirPath, dirNames, fileNames in os.walk(directory):
        for filename in fileNames:
            if filename.endswith(".properties") or filename.endswith('.yml') or filename.endswith('.yaml'):
                file_path = os.path.join(dirPath, filename)
                with open(file_path, 'r', encoding='utf-8') as data:
                    data = data.readlines()
                    for line in data:
                        # 匹配 properties 文件
                        if line.startswith('server.servlet.context-path'):
                            context = line.split('=')[1].strip()
                            print(Fore.BLUE + "[*]Found context-path:" + context)
                            return context
                        # 匹配 yml 文件
                        elif line.find('context-path') > -1:
                            context = line.strip().split(':')[1].strip()
                            print(Fore.BLUE + "[*]Found context-path:" + context)
                            return context
                        else:
                            continue
    return None


def extract_routes_from_file(file_path, directory, context):
    routes = []
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
        # 找到Controller注解对应的Controller类
        if re.search('@(?!(ControllerAdvice))(|Rest)Controller', content):
            parent_route, public_class_line = get_class_parent_route(content)
            content_lines = content.split('\n')
            # 提取类名定义所在行后的所有代码
            content_after_public_class = content_lines[public_class_line:]
            global route_num
            for i, line in enumerate(content_after_public_class):
                try:
                    if re.search(mapping_pattern, line):
                        route_define = line.strip()
                        # 如果路由映射的定义逻辑在一行代码中完全覆盖
                        if route_define.endswith(')'):
                            route_define = route_define
                        # 如果路由映射的定义逻辑在多行代码中才覆盖
                        else:
                            q = i + 1
                            while q < len(content_after_public_class) and not content_after_public_class[q].strip().endswith(')'):
                                route_define += '' + content_after_public_class[q].strip()
                                q += 1
                            route_define += '' + content_after_public_class[q].strip()
                        # print(Fore.RED + route_define)
                        # 判断下路由信息是通过字符串字节提供的，还是通过常量提供的，然后统一提取出字符串值
                        if re.search(r'\("', route_define):
                            route = extract_value_between_quotes(route_define)
                        else:
                            route = get_path_value(route_define, directory)
                        # 获取完整的一条路由信息
                        if parent_route is not None and route is not None:
                            route = parent_route + route
                        # 向下遍历找到函数的定义，此处考虑了路由注解下方可能还携带多个其它用途的注解
                        j = i + 1
                        while j < len(content_after_public_class) and not content_after_public_class[j].strip().startswith('public'):
                            j += 1
                        method_define = content_after_public_class[j].strip()
                        # 获取函数定义的行级代码，考虑函数定义可能跨越多行，需进行代码合并，获得完整的函数定义，否则可能导致函数参数提取残缺
                        q = j
                        while j < len(content_after_public_class) and not content_after_public_class[q].strip().endswith('{'):
                            q += 1
                            method_define = method_define + '' + content_after_public_class[q].strip()
                        # print(route)
                        # print(method_define)
                        return_type, function_name, parameters = extract_function_details(method_define)
                        route_info = {
                            'context': context,
                            'parent_route': parent_route,
                            'route': route,
                            'request': get_request_type(route_define),
                            'return_type': return_type,
                            'method_name': function_name,
                            'parameters': parameters,
                            'file_path': file_path,
                        }
                        routes.append(route_info)
                        print(Fore.GREEN + '[%s]' % str(route_num) + str(route_info))
                        route_num += 1
                except Exception as e:
                    print(Fore.RED + '[-]' + str(file) + ' ' + str(e))
                    continue
    return routes


def scan_project_directory(directory):
    context = extract_context_path(directory)
    all_routes = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.java'):
                file_path = os.path.join(root, file)
                routes = extract_routes_from_file(file_path, directory, context)
                if routes:
                    all_routes.extend(routes)
    return all_routes


if __name__ == '__main__':
    project_directory = input("Enter the path to your Spring Boot project: ")
    # project_directory1 = r'D:\Code\Java\Github\java-sec-code-master'
    # project_directory2 = r'D:\Code\Java\Github\java-sec-code-master\src\main\java\org\joychou\controller\othervulns'
    # project_directory3 = r'D:\Code\Java\Github\RuoYi-master'
    # project_directory4 = r'D:\Code\Java\WebGoat-2023.8'
    # project_directory5 = r'D:\Code\Java\WebGoat-2023.8\src\main\java\org\owasp\webgoat\container\service'
    routes_info = scan_project_directory(project_directory)
    write_routes_to_xlsx(routes_info)
