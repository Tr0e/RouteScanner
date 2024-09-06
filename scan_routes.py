"""
@File：scan_routes.py
@Time：2024/8/29
@Auth：Tr0e
@Github：https://github.com/Tr0e
@Description：基于正则表达式，批量自动化解析多项目源代码的路由信息，生成可视化表格，辅助代码审计统计
@版本迭代：
v1.0.0 20240829，首版本开发完成；
v1.1.0 20240830，修复父级路由识别的已知Bug；
v1.2.0 20240831，添加对多个maven项目同时扫描的功能；
v2.0.0 20240906，支持通过参数指定将所有路由集中在一个sheet，新增Project、Annotation（注解）两列；
"""
import os
import re
import argparse
import pandas as pd
from colorama import Fore, init
from openpyxl import load_workbook

# 配置colorama颜色自动重置，否则得手动设置Style.RESET_ALL
init(autoreset=True)

# 统计路由数量的全局变量
route_num = 1
# 正则表达式来匹配Spring的路由注解、方法返回类型、方法名称和参数
mapping_pattern = re.compile(r'@(Path|(Request|Get|Post|Put|Delete|Patch)Mapping)\(')


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


def extract_routes_from_file(file_path, directory, folder, context):
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

                        # 向下遍历找到函数的定义的首行代码位置，此处考虑了路由注解下方可能还携带多个其它用途的注解
                        method_start_line = i + 1
                        while method_start_line < len(content_after_public_class) and not content_after_public_class[method_start_line].strip().startswith('public'):
                            method_start_line += 1
                        method_define = content_after_public_class[method_start_line].strip()
                        # 获取函数定义的行级代码，考虑函数定义可能跨越多行，需进行代码合并，获得完整的函数定义，否则可能导致函数参数提取残缺
                        method_end_line = method_start_line
                        while method_start_line < len(content_after_public_class) and not content_after_public_class[method_end_line].strip().endswith('{'):
                            method_end_line += 1
                            method_define = method_define + '' + content_after_public_class[method_end_line].strip()
                        # print(route)
                        # print(method_define)
                        # 解析函数定义的返回值、函数名、函数参数
                        return_type, function_name, parameters = extract_function_details(method_define)

                        # 获得函数对应的所有注解信息，查找函数定义所在行上方的第一个空行之前的所有数据
                        annotation = []
                        for j in range(method_start_line - 1, -1, -1):  # 从当前行往上查找
                            if content_after_public_class[j].strip() == '':  # 空行
                                break
                            annotation.append(content_after_public_class[j].strip())  # 添加当前行到结果列表
                        annotation.reverse()
                        # print(Fore.RED + str(annotation))

                        route_info = {
                            'project': folder,
                            'context': context,
                            'file': str(file_path.split('\\')[-1]).split('.java')[0],
                            'parent_route': parent_route,
                            'route': route,
                            'request': get_request_type(route_define),
                            'return_type': return_type,
                            'method_name': function_name,
                            'parameters': parameters,
                            'annotation': str(annotation),
                            'file_path': file_path,
                        }
                        routes.append(route_info)
                        print(Fore.GREEN + '[%s]' % str(route_num) + str(route_info))
                        route_num += 1
                except Exception as e:
                    print(Fore.RED + '[-]' + str(file) + ' ' + str(e))
                    continue
    return routes


def find_all_pom_files(directory):
    """
    遍历寻找指定目录下的所有 pom.xml 文件，并建立一个字典，存储文件夹名称和其绝对路径。
    """
    pom_dict = {}  # 初始化字典存储结果
    # 遍历目录及其所有子目录
    for dirPath, dirNames, fileNames in os.walk(directory):
        # 检查当前目录中的是否包含pom.xml文件和src子文件夹，需同时满足才认为当前是个maven项目根路径
        if 'pom.xml' in fileNames and 'src' in dirNames:
            # 获取目录名称
            folder_name = os.path.basename(dirPath)
            # 将目录名称和绝对路径添加到字典中
            pom_dict[folder_name] = os.path.abspath(dirPath)
    return pom_dict


def write_routes_to_xlsx(all_data_list, folder_name, sheet_rule):
    """
    将路由信息写入Excel文件
    """
    dataSource = {
        "Project": [item['project'] for item in all_data_list],
        "Context": [item['context'] for item in all_data_list],
        "File": [item['file'] for item in all_data_list],
        "Parent Route": [item['parent_route'] for item in all_data_list],
        "Route": [item['route'] for item in all_data_list],
        "Request": [item['request'] for item in all_data_list],
        "Method Name": [item['method_name'] for item in all_data_list],
        "Return Type": [item['return_type'] for item in all_data_list],
        "Parameters": [item['parameters'] for item in all_data_list],
        "Annotation": [item['annotation'] for item in all_data_list],
        "File Path": [item['file_path'] for item in all_data_list],
    }
    if not os.path.exists('Data.xlsx'):
        # 本地xlsx文件不存在，创建一个全新的工作簿
        with pd.ExcelWriter('Data.xlsx', engine='openpyxl') as writer:
            # 创建一个新的 Sheet
            dataFrame = pd.DataFrame(dataSource)
            if sheet_rule == 'one':
                dataFrame.to_excel(writer, sheet_name='all_routes', index=False)
            elif sheet_rule == 'more':
                dataFrame.to_excel(writer, sheet_name=folder_name, index=False)
    else:
        existing_book = load_workbook('Data.xlsx')
        with pd.ExcelWriter('Data.xlsx', engine='openpyxl', mode='a', if_sheet_exists='overlay') as writer:
            # 获取已有工作簿的工作表字典
            existing_worksheets = existing_book.worksheets
            existing_sheet_names = [ws.title for ws in existing_worksheets]
            new_dataFrame = pd.DataFrame(dataSource)
            # 如果目标工作表不存在，则创建新的工作表并写入数据
            if sheet_rule == 'more' and folder_name not in existing_sheet_names:
                new_dataFrame.to_excel(writer, sheet_name=folder_name, index=False)
            elif sheet_rule == 'one':
                # 如果目标工作表已存在，加载该工作表并追加数据
                new_df_without_index = new_dataFrame.copy()
                new_df_without_index.reset_index(drop=True, inplace=True)
                combined_df = pd.concat([pd.read_excel('Data.xlsx', sheet_name='all_routes'), new_df_without_index], ignore_index=False)
                combined_df.to_excel(writer, sheet_name='all_routes', index=False)
    print(Fore.BLUE + "[*]Successfully saved data to xlsx!")


def scan_project_directory(directory, sheet_rule):
    # 判断本路径下Data.xlsx文件是否存在，存在的话先删除
    if os.path.exists('Data.xlsx'):
        os.remove('Data.xlsx')
    pom_files = find_all_pom_files(directory)
    # 遍历所有pom.xml文件对应的项目路径，收集路由信息
    for folder_name, folder_path in pom_files.items():
        print(Fore.YELLOW + f"[+]Folder Name: {folder_name}, Folder Path: {folder_path}")
        context = extract_context_path(folder_path)
        all_routes = []
        for root, _, files in os.walk(folder_path):
            for file in files:
                if file.endswith('.java'):
                    file_path = os.path.join(root, file)
                    routes = extract_routes_from_file(file_path, folder_path, folder_name, context)
                    if routes:
                        all_routes.extend(routes)
        # 判断当前携带pom.xml文件的项目文件夹下提取的路由信息字典是否为空
        if all_routes:
            write_routes_to_xlsx(all_routes, folder_name, sheet_rule)
        else:
            print(Fore.RED + f"[-]No routes found in this project path: {folder_path}/{folder_name}…")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-sheet',
                        help='Use "one" or "more" to specify whether the generated routing information is concentrated in one sheet or divided into multiple sheets by project.')
    parser.add_argument('-dir',
                        help='Specify the code path to be scanned')
    args = parser.parse_args()
    if args.sheet is not None and args.dir is not None:
        scan_project_directory(args.dir, args.sheet.lower())
    else:
        print(Fore.RED + "[!]Please fully specify the -sheet and -dir parameters and values. For help, try the -h parameter.")
